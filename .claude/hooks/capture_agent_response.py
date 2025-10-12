"""
Hook to capture agent responses from Stop event - Windows Version
Reads the transcript to extract the latest agent response.
"""
import json
import sys
import os
from datetime import datetime, timezone
from claude_code_capture_utils import get_log_file_path, add_ab_metadata_to_log_entry

def read_transcript_jsonl(transcript_path):
    """Read and parse JSONL transcript file."""
    try:
        if not os.path.exists(transcript_path):
            return []
        
        entries = []
        with open(transcript_path, "r", encoding="utf-8") as f:
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

def extract_latest_agent_response(transcript_entries):
    """Extract the most recent assistant message and usage data from transcript."""
    for entry in reversed(transcript_entries):
        # Check if this is an assistant message (role is nested in message object)
        message = entry.get("message", {})
        if message.get("role") == "assistant":
            content = message.get("content", [])
            usage = message.get("usage", {})
            return content, usage
    return [], {}

def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        # Extract relevant data
        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path", "")
        cwd = input_data.get("cwd", "")
        stop_hook_active = input_data.get("stop_hook_active", False)
        
        # Read transcript to get the latest agent response and usage data
        transcript_entries = read_transcript_jsonl(transcript_path)
        agent_content, usage_data = extract_latest_agent_response(transcript_entries)
        
        # Create log entry
        log_entry = {
            "event_type": "assistant_response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "transcript_path": transcript_path,
            "cwd": cwd,
            "stop_hook_active": stop_hook_active,
            "content": {
                "assistant_response": agent_content,
                "usage": usage_data if usage_data else None
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
        print(f"Error capturing assistant response: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

