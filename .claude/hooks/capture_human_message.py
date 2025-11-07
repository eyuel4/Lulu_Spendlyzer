"""
Hook to capture human messages (user prompts) from UserPromptSubmit event - Windows Version
Logs to JSON file with timestamp and session info.
"""
import json
import sys
import os
from datetime import datetime, timezone
from claude_code_capture_utils import get_log_file_path, add_ab_metadata_to_log_entry

def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        # Extract relevant data
        session_id = input_data.get("session_id", "unknown")
        prompt = input_data.get("prompt", "")
        transcript_path = input_data.get("transcript_path", "")
        cwd = input_data.get("cwd", "")
        
        # Create log entry
        log_entry = {
            "event_type": "human_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "transcript_path": transcript_path,
            "cwd": cwd,
            "content": {
                "prompt": prompt
            }
        }
        
        # Add A/B testing metadata
        log_entry = add_ab_metadata_to_log_entry(log_entry, cwd)
        
        # Get correct log file path (routes to model-specific directory for A/B testing)
        log_file = get_log_file_path(session_id, cwd)
        
        # Append to session log file (JSONL format)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"Error capturing human message: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

