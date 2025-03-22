# files-to-prompt-strajk Specification

## Capabilities

- Concatenates files into Claude XML format for LLM prompting
- Processes directories recursively (configurable with glob patterns)
- Filters files by extension
- Respects .gitignore rules (can be disabled)
- Extracts and includes SQLite database schemas
- Adds line numbers to file content (optional)
- Handles file paths from stdin or command line arguments
- Writes output to stdout or file
- Analyzes token counts using tiktoken library
- Displays file statistics in tree format
- Auto-detects and skips binary files
- Processes relative paths based on specified working directory

## Statistics Tracking

- Tracks token counts for all processed files
- Shows relative paths in stats tree output
- Displays token counts inline with file/directory names
- Provides total token count across all files
- Supports stats-only mode without generating document content

## Limitations

- No markdown output support (Claude XML only)
- Binary files always skipped (not configurable)
- No streaming output option
- No built-in file content transformation
- No custom tokenizer support (uses tiktoken only)
- No parallel/multi-threaded processing
- Cannot selectively include specific binary file types
- No direct integration with LLM APIs
