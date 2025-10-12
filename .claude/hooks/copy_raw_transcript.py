"""
Copy raw transcript to logs folder for complete data preservation - Windows Version
This hook runs on SessionEnd to copy the complete raw transcript.
"""
import json
import sys
import os
import shutil
from pathlib import Path
from claude_code_capture_utils import detect_model_lane, get_experiment_root

def copy_raw_transcript():
    """Copy the raw transcript file to our logs folder with _raw suffix."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        
        session_id = input_data.get('session_id')
        transcript_path = input_data.get('transcript_path')
        cwd = input_data.get('cwd', os.getcwd())
        
        if not session_id or not transcript_path:
            print(f"Missing session_id or transcript_path", file=sys.stderr)
            return
        
        # Detect A/B testing setup
        model_lane = detect_model_lane(cwd)
        experiment_root = get_experiment_root(cwd)
        
        if model_lane and experiment_root:
            # A/B testing mode - route to model-specific logs directory
            logs_dir = Path(experiment_root) / "logs" / model_lane
            logs_dir.mkdir(parents=True, exist_ok=True)
            dest_path = logs_dir / f"session_{session_id}_raw.jsonl"
        else:
            # Fallback to current behavior
            project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
            logs_dir = Path(project_dir) / "logs"
            logs_dir.mkdir(exist_ok=True)
            dest_path = logs_dir / f"session_{session_id}_raw.jsonl"
        
        # Define source path
        source_path = Path(transcript_path)
        
        # Copy the raw transcript if it exists
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"[OK] Copied raw transcript to {dest_path}")
        else:
            print(f"Warning: Raw transcript not found at {source_path}", file=sys.stderr)
            
    except Exception as e:
        print(f"Error copying raw transcript: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    copy_raw_transcript()

