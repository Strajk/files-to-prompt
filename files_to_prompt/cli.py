import os
import sys
import sqlite3
from fnmatch import fnmatch
from files_to_prompt.utils import allowed_by_gitignore
import pathlib
import click

global_index = 1
processed_paths = set()

def add_line_numbers(content):
    lines = content.splitlines()
    padding = len(str(len(lines)))
    numbered_lines = [f"{i + 1:{padding}}  {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered_lines)

def print_document(writer, path, content, line_numbers):
    global global_index
    if line_numbers:
        content = add_line_numbers(content)
    writer(f'<document path="{path}" index="{global_index}">')
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
): 
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
                    dirs[:] = [
                        d
                        for d in dirs
                        if not any(fnmatch(d, pattern) for pattern in ignore_patterns)
                    ]
                files = [
                    f
                    for f in files
                    if not any(fnmatch(f, pattern) for pattern in ignore_patterns)
                ]

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
                print_document(writer, file_path, content, line_numbers)
            except Exception as e:
                warning_message = f"Warning: Error processing SQLite file {file_path}: {str(e)}"
                click.echo(click.style(warning_message, fg="red"), err=True)
        else:
            try:
                with open(file_path, "r") as f:
                    print_document(writer, file_path, f.read(), line_numbers)
            except UnicodeDecodeError:
                warning_message = f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                click.echo(click.style(warning_message, fg="red"), err=True)

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

    # Read paths from stdin if available
    stdin_paths = read_paths_from_stdin(use_null_separator=null)

    # Combine paths from arguments and stdin
    paths = [*paths, *stdin_paths]

    writer = click.echo
    fp = None
    if output_file:
        fp = open(output_file, "w", encoding="utf-8")
        writer = lambda s: print(s, file=fp)

    if len(paths) > 0:
        writer("<documents>")
        for path in paths:
            if not os.path.exists(path):
                raise click.BadArgumentUsage(f"Path does not exist: {path}")
            process_path(
                path,
                extensions,
                include_hidden,
                ignore_files_only,
                ignore_gitignore,
                ignore_patterns,
                writer,
                line_numbers,
                extract_sqlite,
            )
        writer("</documents>")
    else:
        raise click.BadArgumentUsage("No paths provided")

    if fp:
        fp.close()

# Note: Not sure if best practice
if __name__ == "__main__":
    cli()