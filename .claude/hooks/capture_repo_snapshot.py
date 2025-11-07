"""
Hook to capture repository snapshots and git metrics - Windows Version
Handles both SessionStart (initial snapshot) and SessionEnd (final snapshot + git diff + metrics).
"""
import json
import sys
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

def detect_model_lane(cwd):
    """Detect if we're in model_a or model_b directory."""
    path_parts = Path(cwd).parts
    if 'model_a' in path_parts:
        return 'model_a'
    elif 'model_b' in path_parts:
        return 'model_b'
    return None

def get_experiment_root(cwd):
    """Get the experiment root directory (parent of model_a/model_b)."""
    current_path = Path(cwd)
    
    # Check if we're inside a model_a or model_b directory
    # Look for the parent that contains both model_a and model_b
    for parent in [current_path] + list(current_path.parents):
        if (parent / 'model_a').exists() and (parent / 'model_b').exists():
            return str(parent)
        # Also check one level up (in case we're inside the cloned repo)
        parent_up = parent.parent
        if (parent_up / 'model_a').exists() and (parent_up / 'model_b').exists():
            return str(parent_up)
    return None

def create_repository_snapshot_zip(source_dir, zip_file_path):
    """Create a zip file of the repository, excluding system files and .git/.claude directories."""
    try:
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        
        # Files and directories to exclude
        exclude_patterns = {'.git', '.claude', '.DS_Store', '__pycache__', '.vscode', '.idea', 
                          'node_modules', '.pytest_cache', '.mypy_cache', '*.pyc', '*.pyo'}
        
        def should_exclude(file_path):
            """Check if file should be excluded from snapshot."""
            path_parts = Path(file_path).parts
            name = os.path.basename(file_path)
            
            # Check if any part of the path matches exclude patterns
            for part in path_parts:
                if part in exclude_patterns or part.startswith('.'):
                    # Allow some common dotfiles but exclude system ones
                    if part not in {'.gitignore', '.env.example', '.dockerignore'}:
                        return True
            
            # Check filename patterns
            if name.endswith(('.pyc', '.pyo', '.DS_Store')):
                return True
                
            return False
        
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            source_path = Path(source_dir)
            
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(source_path)
                    
                    if not should_exclude(str(relative_path)):
                        zipf.write(file_path, relative_path)
        
        return True
        
    except Exception as e:
        print(f"Error creating repository snapshot zip: {e}", file=sys.stderr)
        return False

def read_session_log(log_file_path):
    """Read and parse session log JSONL file."""
    try:
        if not os.path.exists(log_file_path):
            return []
        
        entries = []
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries
    except Exception:
        return []

def get_base_commit_from_session_log(experiment_root, model_lane, session_id):
    """Get base commit from session start log entry."""
    try:
        log_file = os.path.join(experiment_root, "logs", model_lane, f"session_{session_id}.jsonl")
        entries = read_session_log(log_file)
        
        # Find session_start entry with git_metadata
        for entry in entries:
            if (entry.get("event_type") == "session_start" and 
                "git_metadata" in entry.get("content", {})):
                git_metadata = entry["content"]["git_metadata"]
                base_commit = git_metadata.get("base_commit")
                if base_commit:
                    return base_commit
        
        return None
        
    except Exception as e:
        print(f"Error reading base commit from session log: {e}", file=sys.stderr)
        return None

def generate_git_diff(repo_dir, output_file, base_commit):
    """Generate git diff from base commit to current state, excluding .claude folder."""
    try:
        # Change to repository directory
        original_cwd = os.getcwd()
        os.chdir(repo_dir)
        
        if not base_commit:
            print(f"No base commit provided for git diff", file=sys.stderr)
            os.chdir(original_cwd)
            return False
        
        # Add untracked files with intent-to-add so they appear in diff (filtered to exclude system files)
        excluded_patterns = ['.claude/', '__pycache__/', 'node_modules/', '.mypy_cache/', 
                           '.pytest_cache/', '.DS_Store', '.vscode/', '.idea/']
        
        untracked_result = subprocess.run(
            ['git', 'ls-files', '--others', '--exclude-standard'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if untracked_result.returncode == 0 and untracked_result.stdout.strip():
            untracked_files = []
            for file in untracked_result.stdout.strip().split('\n'):
                file = file.strip()
                # Filter out files matching exclusion patterns
                if file and not any(pattern in file for pattern in excluded_patterns):
                    untracked_files.append(file)
            
            # Add filtered untracked files with intent-to-add
            for file in untracked_files:
                subprocess.run(
                    ['git', 'add', '-N', file],
                    capture_output=True,
                    timeout=5
                )
        
        # Generate git diff from base commit to current working directory, excluding system files
        result = subprocess.run(
            ['git', 'diff', base_commit, '--', '.', 
             ':!.claude', ':!**/.mypy_cache', ':!**/__pycache__', ':!**/.pytest_cache',
             ':!**/.DS_Store', ':!**/node_modules', ':!**/.vscode', ':!**/.idea'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Write diff to file (even if empty)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            return True
        else:
            print(f"Git diff command failed: {result.stderr}", file=sys.stderr)
            return False
        
    except Exception as e:
        print(f"Error generating git diff: {e}", file=sys.stderr)
        if 'original_cwd' in locals():
            os.chdir(original_cwd)
        return False

def calculate_git_metrics(repo_dir, base_commit):
    """Calculate git metrics using git diff --numstat from base commit, excluding .claude folder."""
    try:
        original_cwd = os.getcwd()
        os.chdir(repo_dir)
        
        if not base_commit:
            print(f"No base commit provided for git metrics", file=sys.stderr)
            os.chdir(original_cwd)
            return {"files_changed_count": 0, "lines_of_code_changed_count": 0}
        
        # Use git diff --numstat from base commit to current working directory, excluding system files
        result = subprocess.run(
            ['git', 'diff', '--numstat', base_commit, '--', '.', 
             ':!.claude', ':!**/.mypy_cache', ':!**/__pycache__', ':!**/.pytest_cache',
             ':!**/.DS_Store', ':!**/node_modules', ':!**/.vscode', ':!**/.idea'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        os.chdir(original_cwd)
        
        if result.returncode != 0:
            print(f"Git diff --numstat failed: {result.stderr}", file=sys.stderr)
            return {"files_changed_count": 0, "lines_of_code_changed_count": 0}
        
        # Parse numstat output
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        files_changed = 0
        total_lines_changed = 0
        
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 3:
                    try:
                        added = int(parts[0]) if parts[0] != '-' else 0
                        removed = int(parts[1]) if parts[1] != '-' else 0
                        files_changed += 1
                        total_lines_changed += added + removed
                    except ValueError:
                        continue
        
        return {
            "files_changed_count": files_changed,
            "lines_of_code_changed_count": total_lines_changed
        }
        
    except Exception as e:
        print(f"Error calculating git metrics: {e}", file=sys.stderr)
        if 'original_cwd' in locals():
            os.chdir(original_cwd)
        return {"files_changed_count": 0, "lines_of_code_changed_count": 0}

def main():
    try:
        # Get event type from command line argument
        if len(sys.argv) < 2:
            print("Usage: capture_repo_snapshot.py [start|end]", file=sys.stderr)
            sys.exit(1)
        
        event_type = sys.argv[1].lower()
        if event_type not in ["start", "end"]:
            print("Event type must be 'start' or 'end'", file=sys.stderr)
            sys.exit(1)
        
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        # Extract relevant data
        session_id = input_data.get("session_id", "unknown")
        cwd = input_data.get("cwd", os.getcwd())
        
        # Detect model lane and experiment root
        model_lane = detect_model_lane(cwd)
        experiment_root = get_experiment_root(cwd)
        
        if not model_lane or not experiment_root:
            print(f"Could not detect model lane or experiment root from {cwd}", file=sys.stderr)
            sys.exit(1)
        
        # Set up paths
        snapshots_dir = os.path.join(experiment_root, "snapshots")
        os.makedirs(snapshots_dir, exist_ok=True)
        
        if event_type == "start":
            # Take initial repository snapshot as zip
            snapshot_zip = os.path.join(snapshots_dir, f"{model_lane}_start.zip")
            success = create_repository_snapshot_zip(cwd, snapshot_zip)
            
            if success:
                print(f"[OK] Created start snapshot zip for {model_lane}")
            else:
                print(f"[ERROR] Failed to create start snapshot zip for {model_lane}", file=sys.stderr)
                
        elif event_type == "end":
            # Take final repository snapshot as zip
            snapshot_zip = os.path.join(snapshots_dir, f"{model_lane}_end.zip")
            success = create_repository_snapshot_zip(cwd, snapshot_zip)
            
            if success:
                print(f"[OK] Created end snapshot zip for {model_lane}")
            
            # Get base commit from session start log
            base_commit = get_base_commit_from_session_log(experiment_root, model_lane, session_id)
            
            if not base_commit:
                print(f"Warning: Could not find base commit for {model_lane}, skipping git diff and metrics", file=sys.stderr)
                return
            
            # Generate git diff using base commit
            diff_file = os.path.join(snapshots_dir, f"{model_lane}_diff.patch")
            diff_success = generate_git_diff(cwd, diff_file, base_commit)
            
            if diff_success:
                print(f"[OK] Generated git diff for {model_lane} from {base_commit[:8]}")
            
            # Note: Git metrics are now calculated directly in generate_session_summary.py
            # No need to update session summary here to avoid duplicates
            
    except Exception as e:
        print(f"Error in repository snapshot capture: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

