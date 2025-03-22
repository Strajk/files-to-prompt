# Snapshot Tests

This directory contains snapshot test results from running the files-to-prompt CLI on various repositories.

## Purpose

These snapshots serve as regression tests to ensure that changes to the files-to-prompt tool don't unexpectedly alter the tool's output. They capture the expected behavior of the CLI for reference and comparison during development.

## Structure

Each repository has its own subdirectory containing:
- `YYYYMMDD_standard.xml`: Output from running the CLI without the `--stats` flag
- `YYYYMMDD_stats.txt`: Output from running the CLI with the `--stats` flag

The YYYYMMDD prefix represents the date when the snapshot was generated.

## Repositories

The following repositories are used for testing:
- `smolagents`: https://github.com/huggingface/smolagents
- `transformers.js`: https://github.com/huggingface/transformers.js
- `crawlee`: https://github.com/apify/crawlee
- `crawlee-python`: https://github.com/apify/crawlee-python

## Running the Tests

To generate new snapshots:

```bash
python tests/test_snapshots.py
```

To generate new snapshots and clean up the cloned repositories afterward:

```bash
python tests/test_snapshots.py --cleanup
```
