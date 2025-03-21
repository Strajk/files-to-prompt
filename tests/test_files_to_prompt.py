import os
import pytest
import re
from click.testing import CliRunner
from files_to_prompt.cli import cli

def filenames_from_cxml(cxml_string):
    "Return set of filenames from document path attributes"
    return set(re.findall(r'<document path="([^"]+)"', cxml_string))

def test_basic_functionality(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "<documents>" in result.output
        assert '<document path="test_dir/file1.txt" index="1">' in result.output
        assert "Contents of file1" in result.output
        assert '<document path="test_dir/file2.txt" index="2">' in result.output
        assert "Contents of file2" in result.output
        assert "</documents>" in result.output

def test_include_hidden(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.hidden.txt", "w") as f:
            f.write("Contents of hidden file")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/.hidden.txt" not in result.output

        result = runner.invoke(cli, ["test_dir", "--include-hidden"])
        assert result.exit_code == 0
        assert '<document path="test_dir/.hidden.txt"' in result.output
        assert "Contents of hidden file" in result.output

def test_ignore_gitignore(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        os.makedirs("test_dir/nested_include")
        os.makedirs("test_dir/nested_ignore")
        with open("test_dir/.gitignore", "w") as f:
            f.write("ignored.txt")
        with open("test_dir/ignored.txt", "w") as f:
            f.write("This file should be ignored")
        with open("test_dir/included.txt", "w") as f:
            f.write("This file should be included")
        with open("test_dir/nested_include/included2.txt", "w") as f:
            f.write("This nested file should be included")
        with open("test_dir/nested_ignore/.gitignore", "w") as f:
            f.write("*")
        with open("test_dir/nested_ignore/nested_ignore.txt", "w") as f:
            f.write("This nested file should not be included")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        filenames = filenames_from_cxml(result.output)

        assert filenames == {
            "test_dir/included.txt",
            "test_dir/nested_include/included2.txt",
        }

        result2 = runner.invoke(cli, ["test_dir", "--ignore-gitignore"])
        assert result2.exit_code == 0
        filenames2 = filenames_from_cxml(result2.output)

        assert filenames2 == {
            "test_dir/included.txt",
            "test_dir/ignored.txt",
            "test_dir/nested_include/included2.txt",
            "test_dir/nested_ignore/nested_ignore.txt",
        }

def test_multiple_paths(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir1")
        with open("test_dir1/file1.txt", "w") as f:
            f.write("Contents of file1")
        os.makedirs("test_dir2")
        with open("test_dir2/file2.txt", "w") as f:
            f.write("Contents of file2")
        with open("single_file.txt", "w") as f:
            f.write("Contents of single file")

        result = runner.invoke(cli, ["test_dir1", "test_dir2", "single_file.txt"])
        assert result.exit_code == 0
        assert "<documents>" in result.output
        assert '<document path="test_dir1/file1.txt" index="1">' in result.output
        assert "Contents of file1" in result.output
        assert '<document path="test_dir2/file2.txt" index="2">' in result.output
        assert "Contents of file2" in result.output
        assert '<document path="single_file.txt" index="3">' in result.output
        assert "Contents of single file" in result.output
        assert "</documents>" in result.output

def test_ignore_patterns(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir", exist_ok=True)
        with open("test_dir/file_to_ignore.txt", "w") as f:
            f.write("This file should be ignored due to ignore patterns")
        with open("test_dir/file_to_include.txt", "w") as f:
            f.write("This file should be included")

        result = runner.invoke(cli, ["test_dir", "--ignore", "*.txt"])
        assert result.exit_code == 0
        assert "file_to_ignore.txt" not in result.output
        assert "file_to_include.txt" not in result.output

        os.makedirs("test_dir/test_subdir", exist_ok=True)
        with open("test_dir/test_subdir/any_file.txt", "w") as f:
            f.write("This entire subdirectory should be ignored due to ignore patterns")
        result = runner.invoke(cli, ["test_dir", "--ignore", "*subdir*"])
        assert result.exit_code == 0
        assert "test_dir/test_subdir/any_file.txt" not in result.output
        assert '<document path="test_dir/file_to_include.txt"' in result.output

        result = runner.invoke(
            cli, ["test_dir", "--ignore", "*subdir*", "--ignore-files-only"]
        )
        assert result.exit_code == 0
        assert '<document path="test_dir/test_subdir/any_file.txt"' in result.output

def test_specific_extensions(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir/two")
        with open("test_dir/one.txt", "w") as f:
            f.write("This is one.txt")
        with open("test_dir/one.py", "w") as f:
            f.write("This is one.py")
        with open("test_dir/two/two.txt", "w") as f:
            f.write("This is two/two.txt")
        with open("test_dir/two/two.py", "w") as f:
            f.write("This is two/two.py")
        with open("test_dir/three.md", "w") as f:
            f.write("This is three.md")

        result = runner.invoke(cli, ["test_dir", "-e", "py", "-e", "md"])
        assert result.exit_code == 0
        assert ".txt" not in result.output
        assert '<document path="test_dir/one.py"' in result.output
        assert '<document path="test_dir/two/two.py"' in result.output
        assert '<document path="test_dir/three.md"' in result.output

def test_binary_file_warning(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/binary_file.bin", "wb") as f:
            f.write(b"\xff")
        with open("test_dir/text_file.txt", "w") as f:
            f.write("This is a text file")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0

        stdout = result.stdout
        stderr = result.stderr

        assert '<document path="test_dir/text_file.txt"' in stdout
        assert "This is a text file" in stdout
        assert "test_dir/binary_file.bin" not in stdout
        assert (
            "Warning: Skipping file test_dir/binary_file.bin due to UnicodeDecodeError"
            in stderr
        )

def test_output_option(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1.txt")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2.txt")
        output_file = "output.txt"
        result = runner.invoke(cli, ["test_dir", "-o", output_file])
        assert result.exit_code == 0
        assert not result.output
        with open(output_file, "r") as f:
            content = f.read()
            assert "<documents>" in content
            assert '<document path="test_dir/file1.txt" index="1">' in content
            assert "Contents of file1.txt" in content
            assert '<document path="test_dir/file2.txt" index="2">' in content
            assert "Contents of file2.txt" in content
            assert "</documents>" in content

def test_line_numbers(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        test_content = "First line\nSecond line\nThird line\nFourth line\n"
        with open("test_dir/multiline.txt", "w") as f:
            f.write(test_content)

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "1  First line" not in result.output
        assert test_content in result.output

        result = runner.invoke(cli, ["test_dir", "-n"])
        assert result.exit_code == 0
        assert "1  First line" in result.output
        assert "2  Second line" in result.output
        assert "3  Third line" in result.output
        assert "4  Fourth line" in result.output

def test_reading_paths_from_stdin(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir1")
        os.makedirs("test_dir2")
        with open("test_dir1/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir2/file2.txt", "w") as f:
            f.write("Contents of file2")

        result = runner.invoke(cli, input="test_dir1/file1.txt\ntest_dir2/file2.txt")
        assert result.exit_code == 0
        assert '<document path="test_dir1/file1.txt" index="1">' in result.output
        assert "Contents of file1" in result.output
        assert '<document path="test_dir2/file2.txt" index="2">' in result.output
        assert "Contents of file2" in result.output

def test_paths_from_arguments_and_stdin(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir1")
        os.makedirs("test_dir2")
        with open("test_dir1/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir2/file2.txt", "w") as f:
            f.write("Contents of file2")

        result = runner.invoke(
            cli,
            args=["test_dir1"],
            input="test_dir2/file2.txt",
        )
        assert result.exit_code == 0
        assert '<document path="test_dir1/file1.txt" index="1">' in result.output
        assert "Contents of file1" in result.output
        assert '<document path="test_dir2/file2.txt" index="2">' in result.output
        assert "Contents of file2" in result.output

def test_duplicate_paths(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir/subdir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("File 1 contents")
        with open("test_dir/subdir/file2.txt", "w") as f:
            f.write("File 2 contents in subdir")

        result = runner.invoke(cli, ["test_dir", "test_dir/subdir"])
        assert result.exit_code == 0
        assert '<document path="test_dir/file1.txt" index="1">' in result.output
        assert "File 1 contents" in result.output
        assert '<document path="test_dir/subdir/file2.txt" index="2">' in result.output
        assert "File 2 contents in subdir" in result.output

        assert result.output.count('<document path="test_dir/subdir/file2.txt" index="2">') == 1