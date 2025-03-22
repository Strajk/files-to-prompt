import os
import sys
import sqlite3
from fnmatch import fnmatch
from files_to_prompt.utils import allowed_by_gitignore
import pathlib
import click
import tiktoken
from typing import Dict

global_index = 1
processed_paths = set()

# List of binary file extensions to skip by default
BINARY_FILE_EXTENSIONS = (
    # Image formats
    ".ico", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
    # Audio formats
    ".mp3", ".wav", ".ogg", ".flac", ".aac",
    # Video formats
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv",
    # Compiled formats
    ".pyc", ".class", ".o", ".so", ".dll", ".exe",
    # Compressed formats
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    # Database formats
    ".db", ".sqlite",
    # Log files
    ".log",
)

class StatsTracker:
    """Track file statistics, including token counts using tiktoken."""
    def __init__(self, encoding_name="cl100k_base", target_path=None):
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.files: Dict[str, Dict] = {}
        self.total_tokens = 0
        self.total_files = 0
        self.total_processed = 0
        self.target_path = target_path

    def add_file(self, file_path: str, content: str, processed: bool = True):
        tokens = self.encoding.encode(content)
        token_count = len(tokens)
        
        # Only add processed files to total tokens count
        if processed:
            self.total_tokens += token_count
        
        # If target_path is set, make the path relative to it
        if self.target_path and str(file_path).startswith(str(self.target_path)):
            # Create a relative path from the target_path
            rel_path = os.path.relpath(file_path, self.target_path)
            # Ensure path starts with ./ for consistency
            if not rel_path.startswith('./') and not rel_path.startswith('/'):
                rel_path = './' + rel_path
            parts = rel_path.split('/')
        else:
            # Handle absolute paths or paths not under target_path
            if not file_path.startswith('./') and not file_path.startswith('/'):
                file_path = './' + file_path
            parts = file_path.split('/')
            
        # Only add to files dictionary if processed (not binary/skipped)
        if processed:
            self.files[file_path] = {
                'size': len(content),
                'tokens': token_count,
                'processed': processed,
                'parts': parts
            }
        
        self.total_files += 1
        if processed:
            self.total_processed += 1

    def get_top_files_by_tokens(self, n=10):
        """Get the top N files with the most tokens."""
        # Filter for processed files only and sort by token count (descending)
        sorted_files = sorted(
            [(path, data) for path, data in self.files.items() if data['processed']],
            key=lambda x: x[1]['tokens'],
            reverse=True
        )
        return sorted_files[:n]
    
    def get_tree_structure(self):
        """Build a tree structure of files and directories with token counts."""
        tree = {}
        
        # Only include processed files in the tree structure
        for path, data in self.files.items():
            # Skip unprocessed files (binary files)
            if not data['processed']:
                continue
                
            parts = data['parts']
            current = tree
            
            # Navigate through the tree
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {'__files': 0, '__tokens': 0, '__processed': 0}
                
                # Update counts at each level
                current[part]['__files'] += 1
                current[part]['__tokens'] += data['tokens']
                if data['processed']:
                    current[part]['__processed'] += 1
                    
                current = current[part]
            
            # Add the file at the leaf level
            leaf = parts[-1]
            if leaf not in current:
                current[leaf] = {
                    '__files': 1,
                    '__tokens': data['tokens'],
                    '__processed': 1 if data['processed'] else 0,
                    '__is_file': True,
                    '__file_info': {
                        'size': data['size'],
                        'tokens': data['tokens'],
                        'processed': data['processed']
                    }
                }
            else:
                current[leaf]['__files'] += 1
                current[leaf]['__tokens'] += data['tokens']
                if data['processed']:
                    current[leaf]['__processed'] += 1
        
        return tree
    
    def print_tree(self, writer=print):
        """Print the file tree with token statistics."""
        tree = self.get_tree_structure()
        
        # Only output the processed files count
        writer(f"Processed files: {self.total_processed}")
        
        def print_node(node, prefix="", is_last=True, depth=0):
            # Get node name and data
            name, data = node
            
            # Handle the root node differently - print without branch characters
            if depth == 0:
                # Print stats for root
                tokens_count = data['__tokens']
                writer(f"{name} [{tokens_count} tokens]")
            else:  
                # For non-root nodes, use branch characters
                branch = "└─ " if is_last else "├─ "
                
                # Print stats for directories or files
                if not data.get('__is_file', False):
                    tokens_count = data['__tokens']
                    writer(f"{prefix}{branch}{name} [{tokens_count} tokens]")
                else:
                    info = data['__file_info']
                    writer(f"{prefix}{branch}{name} [{info['tokens']} tokens]")
            
            # Calculate prefix for children
            next_prefix = prefix + ("    " if is_last else "│   ")
            
            # Get and sort children items
            items = [(k, v) for k, v in data.items() if not k.startswith('__')]
            items.sort(key=lambda x: (0 if x[1].get('__is_file', False) else 1, x[0]))
            
            # Process children
            for i, item in enumerate(items):
                print_node(item, next_prefix, i == len(items) - 1, depth + 1)
        
        # Process only the root level items
        root_items = [(k, v) for k, v in tree.items()]
        if root_items:
            # Sort root items
            root_items.sort(key=lambda x: (0 if x[1].get('__is_file', False) else 1, x[0]))
            
            # Print the root node directly without any indentation or branch characters
            if len(root_items) == 1:  # Usually we only have one root node
                name, data = root_items[0]
                tokens_count = data['__tokens']
                writer(f"{name} [{tokens_count} tokens]")
                
                # Process children of the root with proper indentation
                items = [(k, v) for k, v in data.items() if not k.startswith('__')]
                items.sort(key=lambda x: (0 if x[1].get('__is_file', False) else 1, x[0]))
                
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    branch = "└─ " if is_last else "├─ "
                    name, data = item
                    
                    if data.get('__is_file', False):
                        info = data['__file_info']
                        writer(f"{branch}{name} [{info['tokens']} tokens]")
                    else:
                        writer(f"{branch}{name} [{data['__tokens']} tokens]")
                    
                    # Process further children with regular print_node
                    next_prefix = "    " if is_last else "│   "
                    subitems = [(k, v) for k, v in data.items() if not k.startswith('__')]
                    subitems.sort(key=lambda x: (0 if x[1].get('__is_file', False) else 1, x[0]))
                    
                    for j, subitem in enumerate(subitems):
                        print_node(subitem, next_prefix, j == len(subitems) - 1, depth=2)
            else:
                # Multiple roots (unlikely but handle it)
                for i, item in enumerate(root_items):
                    is_last = i == len(root_items) - 1
                    print_node(item, "", is_last, depth=0)
        
        # After printing the tree, show the top 10 files by token count
        top_files = self.get_top_files_by_tokens(10)
        if top_files:
            writer("\nTop 10 files by token count:")
            for i, (path, data) in enumerate(top_files, 1):
                # Get the relative path if available
                display_path = path
                if self.target_path and str(path).startswith(str(self.target_path)):
                    display_path = os.path.relpath(path, self.target_path)
                    if not display_path.startswith('./') and not display_path.startswith('/'):
                        display_path = './' + display_path
                        
                writer(f"{i}. {display_path} [{data['tokens']} tokens]")

def add_line_numbers(content):
    lines = content.splitlines()
    padding = len(str(len(lines)))
    numbered_lines = [f"{i + 1:{padding}}  {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered_lines)

def print_document(writer, path, content, line_numbers, root_path=None):
    global global_index
    if line_numbers:
        content = add_line_numbers(content)
        
    # If root_path is provided, make the path relative to it
    display_path = path
    if root_path:
        # Ensure both paths are strings
        path_str = str(path)
        root_path_str = str(root_path)
        
        if path_str.startswith(root_path_str):
            # Get the relative path
            rel_path = os.path.relpath(path_str, root_path_str)
            # Avoid showing './' prefix for files directly in the root
            display_path = rel_path
        
    writer(f'<document path="{display_path}" index="{global_index}">')
    writer(content)
    writer("</document>")
    global_index += 1

def is_sqlite3_file(file_path):
    """Check if the given file is a SQLite3 database."""
    try:
        # Read the first 16 bytes to check for SQLite3 header
        with open(file_path, "rb") as f:
            header = f.read(16)
        return header[:16].startswith(b'SQLite format 3')
    except (IOError, OSError):
        return False

def get_sqlite_schema(file_path):
    """Extract schema information from a SQLite3 database file."""
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        # Get tables schema
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        # Get views schema
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()

        # Get indexes schema
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        indexes = cursor.fetchall()

        # Format the results
        schema_parts = []

        if tables:
            schema_parts.append("-- Tables")
            for table_name, table_sql in tables:
                schema_parts.append(f"{table_sql};")

        if views:
            schema_parts.append("\n-- Views")
            for view_name, view_sql in views:
                schema_parts.append(f"{view_sql};")

        if indexes:
            schema_parts.append("\n-- Indexes")
            for idx_name, idx_sql in indexes:
                schema_parts.append(f"{idx_sql};")

        conn.close()
        return "\n".join(schema_parts)

    except sqlite3.Error as e:
        return f"Error extracting schema: {str(e)}"

def is_binary_file(file_path):
    """Check if a file is a known binary format based on extension."""
    # Check against known binary extensions
    file_lower = str(file_path).lower()
    for ext in BINARY_FILE_EXTENSIONS:
        if file_lower.endswith(ext):
            return True
    
    # For unrecognized extensions, try to read the first chunk and check for nullbytes
    # which is a common indicator of binary content
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Binary files often contain null bytes
            if b'\x00' in chunk:
                return True
            # ASCII files don't typically contain a high percentage of non-ASCII characters
            non_ascii = sum(1 for b in chunk if b > 127)
            if non_ascii > len(chunk) * 0.3:  # 30% of content is non-ASCII
                return True
    except (IOError, OSError):
        # If we can't open the file, default to considering it binary
        return True
    
    return False

def process_path(
    path,
    extensions,
    include_hidden,
    ignore_files_only,
    ignore_gitignore,
    ignore_patterns,
    writer,
    line_numbers=False,
    extract_sqlite=True,
    stats_tracker=None,
    root_path=None,
    stats_only=False,
):
    """Process a file or directory path, generating the document output.
    
    The path is resolved relative to the current working directory,
    which can be modified using the --cwd option in the CLI.
    """ 
    all_files = [path] if os.path.isfile(path) else []
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                files = [f for f in files if not f.startswith(".")]

            root_path = pathlib.Path(root)
            if not ignore_gitignore:
                dirs[:] = [
                    d for d in dirs if allowed_by_gitignore(root_path, root_path / d)
                ]
                files = [
                    f for f in files if allowed_by_gitignore(root_path, root_path / f)
                ]

            if ignore_patterns:
                if not ignore_files_only:
                    filtered_dirs = []
                    for d in dirs:
                        # Get relative path from root_path
                        rel_dir_path = os.path.relpath(os.path.join(root, d), path).replace('\\', '/')
                        # Check if any pattern matches the dir name or path
                        if not any(fnmatch(d, pattern) or fnmatch(rel_dir_path, pattern) for pattern in ignore_patterns):
                            filtered_dirs.append(d)
                    dirs[:] = filtered_dirs
                
                filtered_files = []
                for f in files:
                    # Get relative path from root_path
                    rel_file_path = os.path.relpath(os.path.join(root, f), path).replace('\\', '/')
                    # Check if any pattern matches the filename or path
                    if not any(fnmatch(f, pattern) or fnmatch(rel_file_path, pattern) for pattern in ignore_patterns):
                        filtered_files.append(f)
                files = filtered_files

            if extensions:
                files = [f for f in files if f.endswith(extensions)]

            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in processed_paths:
                    all_files.append(file_path)

    # Sort files to ensure consistent order
    for file_path in sorted(all_files):
        processed_paths.add(file_path)
        if extract_sqlite and is_sqlite3_file(file_path):
            try:
                schema = get_sqlite_schema(file_path)
                content = f"-- SQLite3 Database Schema\n{schema}"
                if not stats_only:
                    print_document(writer, file_path, content, line_numbers, root_path)
                if stats_tracker:
                    stats_tracker.add_file(file_path, content, processed=True)
            except Exception as e:
                warning_message = f"Warning: Error processing SQLite file {file_path}: {str(e)}"
                click.echo(click.style(warning_message, fg="red"), err=True)
                if stats_tracker:
                    stats_tracker.add_file(file_path, f"-- SQLite3 Database Schema Error: {str(e)}", processed=False)
        elif is_binary_file(file_path):
            # Always skip binary files silently
            pass  # Don't track binary files in stats at all
        else:
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    if not stats_only:
                        print_document(writer, file_path, content, line_numbers, root_path)
                    if stats_tracker:
                        stats_tracker.add_file(file_path, content, processed=True)
            except UnicodeDecodeError:
                # Silently skip files with decode errors
                pass  # Don't track files with decode errors in stats

def read_paths_from_stdin(use_null_separator):
    if sys.stdin.isatty():
        # No ready input from stdin, don't block for input
        return []

    stdin_content = sys.stdin.read()
    if use_null_separator:
        paths = stdin_content.split("\0")
    else:
        paths = stdin_content.split()  # split on whitespace
    return [p for p in paths if p]

@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("extensions", "-e", "--extension", multiple=True)
@click.option(
    "--include-hidden",
    is_flag=True,
    help="Include files and folders starting with .",
)
@click.option(
    "--ignore-files-only",
    is_flag=True,
    help="--ignore option only ignores files",
)
@click.option(
    "--ignore-gitignore",
    is_flag=True,
    help="Ignore .gitignore files and include all files",
)
@click.option(
    "ignore_patterns",
    "--ignore",
    multiple=True,
    default=[],
    help="List of patterns to ignore",
)
@click.option(
    "output_file",
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Output to a file instead of stdout",
)
@click.option(
    "line_numbers",
    "-n",
    "--line-numbers",
    is_flag=True,
    help="Add line numbers to the output",
)
@click.option(
    "--null",
    "-0",
    is_flag=True,
    help="Use NUL character as separator when reading from stdin",
)
@click.option(
    "extract_sqlite",
    "--extract-sqlite",
    is_flag=True,
    help="Extract schema information from SQLite3 database files instead of treating them as binary",
)
@click.option(
    "stats",
    "--stats",
    is_flag=True,
    help="Track token statistics for processed files and output a tree at the end",
)
@click.option(
    "cwd",
    "--cwd",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Set the working directory for resolving relative paths",
)
@click.option(
    "--no-ignore-default",
    is_flag=True,
    help="Do not ignore default patterns: .github/workflows, LICENSE, .gitignore, env/venv, node_modules, uv.lock, package-lock.json, yarn.lock",
)

@click.version_option()
def cli(
    paths,
    extensions,
    include_hidden,
    ignore_files_only,
    ignore_gitignore,
    ignore_patterns,
    output_file,
    line_numbers,
    null,
    extract_sqlite,
    stats,
    cwd,
    no_ignore_default,
):
    """
    Takes one or more paths to files or directories and outputs every file,
    recursively, in Claude XML format:

    \b
        <documents>
        <document index="1">
        <source>path/to/file1.txt</source>
        <document_content>
        Contents of file1.txt
        </document_content>
        </document>
        ...
        </documents>
    """
    # Reset globals for pytest
    global global_index, processed_paths
    global_index = 1
    processed_paths = set()
    
    # Set the working directory if specified
    original_cwd = os.getcwd()
    if cwd:
        os.chdir(cwd)
        click.echo(click.style(f"Working directory set to: {cwd}", fg="blue"), err=True)
        
    # Add default ignore patterns if requested
    if not no_ignore_default:
        default_patterns = [
            ".github/workflows/*",
            "LICENSE",
            "LICENSE.md",
            "CONTRIBUTING",
            "CONTRIBUTING.md",
            ".gitignore",
            "**/env/**",
            "**/venv/**",
            "**/node_modules/**",
            "**/uv.lock",
            "**/package-lock.json",
            "**/yarn.lock",
        ]
        ignore_patterns = list(ignore_patterns) + default_patterns
        click.echo(click.style("Added default ignore patterns", fg="blue"), err=True)
    
    # Initialize stats tracker if needed
    stats_tracker = None
    if stats:
        try:
            # If there are paths, use the first path as the target for relative paths in stats
            # If cwd is set, paths are relative to that directory
            target_path = os.path.abspath(paths[0]) if paths else (os.getcwd() if cwd else None)
            stats_tracker = StatsTracker(target_path=target_path)
        except ImportError:
            click.echo(click.style("Warning: tiktoken package not found. Statistics feature disabled.", fg="yellow"), err=True)
            stats = False

    # Read paths from stdin if available
    stdin_paths = read_paths_from_stdin(use_null_separator=null)

    # Combine paths from arguments and stdin
    paths = [*paths, *stdin_paths]

    writer = click.echo
    fp = None
    if output_file:
        fp = open(output_file, "w", encoding="utf-8")
        # Use a proper function instead of lambda to avoid lint warning
        def writer(s):
            print(s, file=fp)

    if len(paths) > 0:
        # Only output XML document tags if not in stats-only mode
        if not stats:
            writer("<documents>")
            
        for path in paths:
            # Convert path to be relative to the specified cwd if needed
            effective_path = path
            if not os.path.exists(effective_path):
                raise click.BadArgumentUsage(f"Path does not exist: {effective_path}")
            # Store the absolute path of the first argument as the root path
            abs_path = os.path.abspath(effective_path)
            root_path = abs_path
            
            process_path(
                path,
                extensions,
                include_hidden,
                ignore_files_only,
                ignore_gitignore,
                ignore_patterns,  # This now includes default patterns if ignore_default is True
                writer,
                line_numbers,
                extract_sqlite,
                stats_tracker,
                root_path,
                stats_only=stats,  # Pass the stats flag as stats_only parameter
            )
            
        if not stats:
            writer("</documents>")
    else:
        raise click.BadArgumentUsage("No paths provided")

    # Print statistics if requested
    if stats and stats_tracker:
        # Use a proper function instead of lambda to avoid lint warning
        if not output_file:
            stats_output = click.echo
        else:
            def stats_output(s):
                print(s, file=fp)
        stats_tracker.print_tree(stats_output)
    
    if fp:
        fp.close()
        
    # Restore the original working directory if it was changed
    if cwd:
        os.chdir(original_cwd)

# Note: Not sure if best practice
if __name__ == "__main__":
    cli()