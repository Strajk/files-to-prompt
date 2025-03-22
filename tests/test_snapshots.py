#!/usr/bin/env python3
"""
Snapshot tests for files-to-prompt CLI.
Clones several repositories and runs files-to-prompt on them to verify output consistency.
"""

import sys
import subprocess
import pathlib
from datetime import datetime

# Path definitions
ROOT_DIR = pathlib.Path(__file__).parent.parent.resolve()
SNAPSHOT_DIR = ROOT_DIR / "tests" / "snapshots"
REPOS_DIR = ROOT_DIR / "tests" / "test_repos"

# Repositories to test
REPOS = {
    "smolagents": "https://github.com/huggingface/smolagents",
    "transformers.js": "https://github.com/huggingface/transformers.js",
    "crawlee": "https://github.com/apify/crawlee",
    "crawlee-python": "https://github.com/apify/crawlee-python",
}

def ensure_dir_exists(path):
    """Ensure directory exists, create if it doesn't."""
    if not path.exists():
        path.mkdir(parents=True)
    return path

def clone_repositories():
    """Clone the test repositories if they don't exist."""
    ensure_dir_exists(REPOS_DIR)
    
    for name, url in REPOS.items():
        repo_path = REPOS_DIR / name
        if not repo_path.exists():
            print(f"Cloning {name} from {url}...")
            subprocess.run(["git", "clone", "--depth=1", url, str(repo_path)], check=True)
        else:
            print(f"Repository {name} already exists, skipping clone.")

def run_command(cmd, output_file=None):
    """Run a command and optionally save output to a file."""
    print(f"Running: {' '.join(cmd)}")
    
    if output_file:
        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
    else:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        print(f"stderr: {result.stderr}")
        return False
    
    return True

def run_command_with_env(cmd, output_file=None, env=None):
    """Run a command with custom environment variables and optionally save output to a file."""
    # Merge provided environment variables with current environment
    current_env = subprocess.os.environ.copy()
    if env:
        current_env.update(env)
    
    cmd_str = ' '.join(cmd)
    env_str = ' '.join(f"{k}={v}" for k, v in env.items()) if env else ''
    print(f"Running with env {env_str}: {cmd_str}")
    
    if output_file:
        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, env=current_env)
    else:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=current_env)
    
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        print(f"stderr: {result.stderr}")
        return False
    
    return True

def generate_snapshots():
    """Generate snapshot files for each repository."""
    ensure_dir_exists(SNAPSHOT_DIR)
    
    # Get the CLI script path
    cli_script = ROOT_DIR / "files_to_prompt" / "cli.py"
    
    timestamp = datetime.now().strftime("%Y%m%d")
    
    for repo_name in REPOS.keys():
        repo_path = REPOS_DIR / repo_name
        if not repo_path.exists():
            print(f"Repository {repo_name} not found, skipping.")
            continue
        
        # Create snapshot directory for this repo
        repo_snapshot_dir = ensure_dir_exists(SNAPSHOT_DIR / repo_name)
        
        # Run without stats flag
        standard_output_file = repo_snapshot_dir / f"{timestamp}_standard.xml"
        run_command([
            sys.executable, str(cli_script), 
            str(repo_path)
        ], standard_output_file)
        
        # Run with stats flag
        stats_output_file = repo_snapshot_dir / f"{timestamp}_stats.txt"
        
        run_command([
            sys.executable, str(cli_script), 
            "--stats", 
            str(repo_path)
        ], stats_output_file)


def main():
    """Main function to run the snapshot tests."""
    # Generate snapshots
    generate_snapshots()
    print(f"Snapshot tests completed. Results saved in {SNAPSHOT_DIR}")

if __name__ == "__main__":
    main()
