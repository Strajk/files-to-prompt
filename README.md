# Fork info

```
uvx --with git+https://github.com/strajk/files-to-prompt files-to-prompt-strajk .
```

```
uv run -m files_to_prompt.cli .
```
- Drop markdown output support, keep only CXML
- Merge #54 - Fix Claude XML for empty paths case
- Merge #52 - Include SQLite3 schemas, and enabled by default
- Merge #51 - Prevent duplicate file processing
- Merge #45 - gitignore implementation based on pathspec
- Remove GitHub Actions workflow for publishing Python package; update test workflow to limit Python versions to 3.12 and 3.13.

Consider:
- ignore defaults https://github.com/TheAhmadOsman/files-to-prompt/commit/c5d5c397ad0f3282ee68387ec3d09ca46a9240c7
- jupyer https://github.com/ncoop57/files-to-prompt/commit/6e945ab214339cb11df4f7dd78d32eed38ae900c
- github repo https://github.com/cheuerde/files-to-prompt/commit/b66fa512cd8fde77e8938bcf8167571eb37c9a3a
- line numbers in brackets https://github.com/omahdi/files-to-prompt/commit/ebde5f24bb84712092df390148e8710d89828e1c


# files-to-prompt

[![PyPI](https://img.shields.io/pypi/v/files-to-prompt.svg)](https://pypi.org/project/files-to-prompt/)
[![Changelog](https://img.shields.io/github/v/release/simonw/files-to-prompt?include_prereleases&label=changelog)](https://github.com/simonw/files-to-prompt/releases)
[![Tests](https://github.com/simonw/files-to-prompt/actions/workflows/test.yml/badge.svg)](https://github.com/simonw/files-to-prompt/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/files-to-prompt/blob/master/LICENSE)

Concatenate a directory full of files into a single prompt for use with LLMs

For background on this project see [Building files-to-prompt entirely using Claude 3 Opus](https://simonwillison.net/2024/Apr/8/files-to-prompt/).

## Installation

Install this tool using `pip`:

```bash
pip install files-to-prompt
```

## Usage

To use `files-to-prompt`, provide the path to one or more files or directories you want to process:

```bash
files-to-prompt path/to/file_or_directory [path/to/another/file_or_directory ...]
```

This will output the contents of every file, with each file preceded by its relative path and separated by `---`.

### Options

- `-e/--extension <extension>`: Only include files with the specified extension. Can be used multiple times.

  ```bash
  files-to-prompt path/to/directory -e txt -e md
  ```

- `--include-hidden`: Include files and folders starting with `.` (hidden files and directories).

  ```bash
  files-to-prompt path/to/directory --include-hidden
  ```

- `--ignore <pattern>`: Specify one or more patterns to ignore. Can be used multiple times. Patterns may match file names and directory names, unless you also specify `--ignore-files-only`. Pattern syntax uses [fnmatch](https://docs.python.org/3/library/fnmatch.html), which supports `*`, `?`, `[anychar]`, `[!notchars]` and `[?]` for special character literals.
  ```bash
  files-to-prompt path/to/directory --ignore "*.log" --ignore "temp*"
  ```

- `--ignore-files-only`: Include directory paths which would otherwise be ignored by an `--ignore` pattern.

  ```bash
  files-to-prompt path/to/directory --ignore-files-only --ignore "*dir*"
  ```

- `--ignore-gitignore`: Ignore `.gitignore` files and include all files.

  ```bash
  files-to-prompt path/to/directory --ignore-gitignore
  ```

- `-o/--output <file>`: Write the output to a file instead of printing it to the console.

  ```bash
  files-to-prompt path/to/directory -o output.txt
  ```

- `-n/--line-numbers`: Include line numbers in the output.

  ```bash
  files-to-prompt path/to/directory -n
  ```
  Example output:
  ```
  files_to_prompt/cli.py
  ---
    1  import os
    2  from fnmatch import fnmatch
    3
    4  import click
    ...
  ```

- `-0/--null`: Use NUL character as separator when reading paths from stdin. Useful when filenames may contain spaces.

  ```bash
  find . -name "*.py" -print0 | files-to-prompt --null
  ```

### Example

Suppose you have a directory structure like this:

```
my_directory/
├── file1.txt
├── file2.txt
├── .hidden_file.txt
├── temp.log
└── subdirectory/
    └── file3.txt
```

Running `files-to-prompt my_directory` will output:

```
my_directory/file1.txt
---
Contents of file1.txt
---
my_directory/file2.txt
---
Contents of file2.txt
---
my_directory/subdirectory/file3.txt
---
Contents of file3.txt
---
```

If you run `files-to-prompt my_directory --include-hidden`, the output will also include `.hidden_file.txt`:

```
my_directory/.hidden_file.txt
---
Contents of .hidden_file.txt
---
...
```

If you run `files-to-prompt my_directory --ignore "*.log"`, the output will exclude `temp.log`:

```
my_directory/file1.txt
---
Contents of file1.txt
---
my_directory/file2.txt
---
Contents of file2.txt
---
my_directory/subdirectory/file3.txt
---
Contents of file3.txt
---
```

If you run `files-to-prompt my_directory --ignore "sub*"`, the output will exclude all files in `subdirectory/` (unless you also specify `--ignore-files-only`):

```
my_directory/file1.txt
---
Contents of file1.txt
---
my_directory/file2.txt
---
Contents of file2.txt
---
```

### Reading from stdin

The tool can also read paths from standard input. This can be used to pipe in the output of another command:

```bash
# Find files modified in the last day
find . -mtime -1 | files-to-prompt
```

When using the `--null` (or `-0`) option, paths are expected to be NUL-separated (useful when dealing with filenames containing spaces):

```bash
find . -name "*.txt" -print0 | files-to-prompt --null
```

You can mix and match paths from command line arguments and stdin:

```bash
# Include files modified in the last day, and also include README.md
find . -mtime -1 | files-to-prompt README.md
```

### Semi "Claude" XML Output

Anthropic has provided [specific guidelines](https://docs.anthropic.com/claude/docs/long-context-window-tips) for optimally structuring prompts to take advantage of Claude's extended context window.

We tweaked it a little to be more readable for humans.


```xml
<documents>
<document path="my_directory/file1.txt" index="1">
Contents of file1.txt
</document>
<document path="my_directory/file2.txt" index="2">
Contents of file2.txt
</document>
</documents>
```
