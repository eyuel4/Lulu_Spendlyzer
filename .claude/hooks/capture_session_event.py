"""
Hook to capture session start/end events - Windows Version
Accepts 'start' or 'end' as command line argument to distinguish the event type.
"""
import json
import sys
import os
import subprocess
from datetime import datetime, timezone
from claude_code_capture_utils import get_log_file_path, add_ab_metadata_to_log_entry

def get_git_metadata(repo_dir):
    """Get current git commit and branch."""
    try:
        # Get current commit hash
        commit_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_dir, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=repo_dir, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        git_metadata = {
            "base_commit": commit_result.stdout.strip() if commit_result.returncode == 0 else None,
            "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Only return metadata if we got at least the commit hash
        if git_metadata["base_commit"]:
            return git_metadata
        else:
            return None
            
    except Exception as e:
        print(f"Warning: Could not capture git metadata: {e}", file=sys.stderr)
        return None

def main():
    try:
        # Get event type from command line argument
        if len(sys.argv) < 2:
            print("Usage: capture_session_event.py [start|end]", file=sys.stderr)
            sys.exit(1)
        
        event_type = sys.argv[1].lower()
        if event_type not in ["start", "end"]:
            print("Event type must be 'start' or 'end'", file=sys.stderr)
            sys.exit(1)
        
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        # Extract relevant data
        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path", "")
        cwd = input_data.get("cwd", "")
        hook_event_name = input_data.get("hook_event_name", "")
        
        # Event-specific data
        content = {}
        if event_type == "start":
            content["source"] = input_data.get("source", "")
            
            # Capture git metadata for session start
            git_metadata = get_git_metadata(cwd)
            if git_metadata:
                content["git_metadata"] = git_metadata
                print(f"[OK] Captured git metadata: {git_metadata['base_commit'][:8]} on {git_metadata['branch']}")
            else:
                print("Warning: Could not capture git metadata", file=sys.stderr)
                
        elif event_type == "end":
            content["reason"] = input_data.get("reason", "")
        
        # Create log entry
        log_entry = {
            "event_type": f"session_{event_type}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "transcript_path": transcript_path,
            "cwd": cwd,
            "hook_event_name": hook_event_name,
            "content": content
        }
        
        # Add A/B testing metadata
        log_entry = add_ab_metadata_to_log_entry(log_entry, cwd)
        
        # Get correct log file path (routes to model-specific directory for A/B testing)
        log_file = get_log_file_path(session_id, cwd)
        
        # Append to session log file (JSONL format)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        # If this is a session end event, generate session summary
        if event_type == "end":
            try:
                project_dir = cwd
                summary_script = os.path.join(project_dir, ".claude", "hooks", "generate_session_summary.py")
                if os.path.exists(summary_script):
                    # Call the summary generator with the same input data
                    result = subprocess.run(
                        [sys.executable, summary_script],
                        input=json.dumps(input_data),
                        text=True,
                        capture_output=True,
                        timeout=30
                    )
                    if result.returncode != 0:
                        print(f"Warning: Session summary generation failed: {result.stderr}", file=sys.stderr)
            except Exception as summary_error:
                print(f"Warning: Could not generate session summary: {summary_error}", file=sys.stderr)
            
    except Exception as e:
        print(f"Error capturing session {event_type} event: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

