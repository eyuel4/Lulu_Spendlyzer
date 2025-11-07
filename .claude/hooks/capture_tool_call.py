"""
Hook to capture tool calls from PreToolUse and PostToolUse events - Windows Version
Accepts 'pre' or 'post' as command line argument to distinguish the event type.
"""
import json
import sys
import os
from datetime import datetime, timezone
from claude_code_capture_utils import get_log_file_path, add_ab_metadata_to_log_entry

def main():
    try:
        # Get event phase from command line argument
        if len(sys.argv) < 2:
            print("Usage: capture_tool_call.py [pre|post]", file=sys.stderr)
            sys.exit(1)
        
        phase = sys.argv[1].lower()
        if phase not in ["pre", "post"]:
            print("Phase must be 'pre' or 'post'", file=sys.stderr)
            sys.exit(1)
        
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        # Extract relevant data
        session_id = input_data.get("session_id", "unknown")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {}) if phase == "post" else None
        transcript_path = input_data.get("transcript_path", "")
        cwd = input_data.get("cwd", "")
        hook_event_name = input_data.get("hook_event_name", "")
        
        # Create log entry
        log_entry = {
            "event_type": f"tool_call_{phase}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "transcript_path": transcript_path,
            "cwd": cwd,
            "hook_event_name": hook_event_name,
            "content": {
                "tool_name": tool_name,
                "tool_input": tool_input
            }
        }
        
        # Add tool response for post events
        if phase == "post" and tool_response is not None:
            log_entry["content"]["tool_response"] = tool_response
        
        # Add A/B testing metadata
        log_entry = add_ab_metadata_to_log_entry(log_entry, cwd)
        
        # Get correct log file path (routes to model-specific directory for A/B testing)
        log_file = get_log_file_path(session_id, cwd)
        
        # Append to session log file (JSONL format)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"Error capturing tool call ({phase}): {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

