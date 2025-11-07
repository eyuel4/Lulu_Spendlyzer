"""
Hook to generate session summary with metrics - Windows Version
Called at the end of a session to analyze the complete session log.
"""
import json
import sys
import os
from datetime import datetime, timezone
from collections import defaultdict, Counter
from claude_code_capture_utils import get_log_file_path, add_ab_metadata_to_log_entry, detect_model_lane, get_experiment_root
import subprocess

def parse_timestamp(timestamp_str):
    """Parse ISO timestamp string to datetime object."""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except:
        return None

def get_git_metrics_from_session(events):
    """Extract git metrics by finding base commit and calculating diff."""
    try:
        # Find base commit from session start event
        base_commit = None
        cwd = None
        
        for event in events:
            if event.get("event_type") == "session_start":
                git_metadata = event.get("content", {}).get("git_metadata", {})
                base_commit = git_metadata.get("base_commit")
                cwd = event.get("cwd")
                break
        
        if not base_commit or not cwd:
            return None
        
        # Calculate git metrics using the base commit
        original_cwd = os.getcwd()
        os.chdir(cwd)
        
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
            return None
        
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
            "lines_of_code_changed_count": total_lines_changed,
            "git_diff_file": f"{detect_model_lane(cwd)}_diff.patch" if detect_model_lane(cwd) else None
        }
        
    except Exception as e:
        print(f"Warning: Could not calculate git metrics: {e}", file=sys.stderr)
        if 'original_cwd' in locals():
            os.chdir(original_cwd)
        return None

def calculate_tool_lines_changed(events):
    """Calculate lines changed directly by Claude Code tools from structuredPatch data."""
    try:
        total_tool_lines_changed = 0
        tool_edits_count = 0
        
        for event in events:
            if event.get("event_type") == "tool_call_post":
                content = event.get("content", {})
                tool_name = content.get("tool_name", "")
                tool_response = content.get("tool_response", {})
                
                # Only count editing tools
                if tool_name in ["Edit", "MultiEdit", "Write"]:
                    # Check for structuredPatch in tool response
                    structured_patch = tool_response.get("structuredPatch", [])
                    
                    for patch in structured_patch:
                        old_lines = patch.get("oldLines", 0)
                        new_lines = patch.get("newLines", 0)
                        # Count net change in lines
                        lines_changed = abs(new_lines - old_lines)
                        total_tool_lines_changed += lines_changed
                        tool_edits_count += 1
        
        return {
            "claude_tool_lines_changed_count": total_tool_lines_changed,
            "claude_tool_edits_count": tool_edits_count
        }
        
    except Exception as e:
        print(f"Warning: Could not calculate tool line changes: {e}", file=sys.stderr)
        return {
            "claude_tool_lines_changed_count": 0,
            "claude_tool_edits_count": 0
        }

def analyze_session_log(log_file_path):
    """Analyze the session log file and extract metrics."""
    if not os.path.exists(log_file_path):
        return None
    
    events = []
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return None
    
    if not events:
        return None
    
    # Initialize counters
    assistant_turns = 0
    human_turns = 0
    tool_calls_successful = defaultdict(int)
    tool_calls_failed = defaultdict(int)
    tool_calls_total = defaultdict(int)
    
    # Initialize usage counters
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation_tokens = 0
    total_cache_read_tokens = 0
    total_ephemeral_5m_tokens = 0
    total_ephemeral_1h_tokens = 0
    service_tier = None
    
    # Track tool call pairs (pre/post) to determine success/failure
    pending_tool_calls = {}  # tool_call_id -> tool_name
    
    # Calculate duration
    timestamps = []
    for event in events:
        if event.get("timestamp"):
            ts = parse_timestamp(event["timestamp"])
            if ts:
                timestamps.append(ts)
    
    total_duration_seconds = 0
    if len(timestamps) >= 2:
        duration = max(timestamps) - min(timestamps)
        total_duration_seconds = duration.total_seconds()
    
    # Analyze events
    for event in events:
        event_type = event.get("event_type", "")
        
        # Count turns
        if event_type == "human_message":
            human_turns += 1
        elif event_type in ["assistant_response", "agent_response"]:  # Handle both old and new terminology
            assistant_turns += 1
            
            # Aggregate usage data from assistant responses
            content = event.get("content", {})
            usage = content.get("usage", {})
            if usage:
                total_input_tokens += usage.get("input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)
                total_cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
                total_cache_read_tokens += usage.get("cache_read_input_tokens", 0)
                
                # Handle cache breakdown
                cache_creation = usage.get("cache_creation", {})
                total_ephemeral_5m_tokens += cache_creation.get("ephemeral_5m_input_tokens", 0)
                total_ephemeral_1h_tokens += cache_creation.get("ephemeral_1h_input_tokens", 0)
                
                # Store service tier (use the last one seen)
                if usage.get("service_tier"):
                    service_tier = usage.get("service_tier")
        
        # Analyze tool calls
        elif event_type == "tool_call_pre":
            content = event.get("content", {})
            tool_name = content.get("tool_name", "unknown")
            # Use a simpler approach - just track that we saw a pre call
            pending_tool_calls[tool_name] = pending_tool_calls.get(tool_name, 0) + 1
            tool_calls_total[tool_name] += 1
            
        elif event_type == "tool_call_post":
            content = event.get("content", {})
            tool_name = content.get("tool_name", "unknown")
            
            # Check if tool call was successful
            tool_response = content.get("tool_response", {})
            
            # Determine success based on response structure
            # Most tools return structured data on success, error messages on failure
            is_successful = True
            if isinstance(tool_response, dict):
                # Check for common error indicators
                if "error" in tool_response or "Error" in str(tool_response):
                    is_successful = False
            elif isinstance(tool_response, str):
                # String responses might indicate errors
                if "error" in tool_response.lower() or "failed" in tool_response.lower():
                    is_successful = False
            
            if is_successful:
                tool_calls_successful[tool_name] += 1
            else:
                tool_calls_failed[tool_name] += 1
            
            # Decrement pending count
            if pending_tool_calls.get(tool_name, 0) > 0:
                pending_tool_calls[tool_name] -= 1
    
    # Handle any remaining pending tool calls as failed
    for tool_name, count in pending_tool_calls.items():
        if count > 0:
            tool_calls_failed[tool_name] += count
    
    # Calculate success rates
    success_rates = {}
    for tool_name in tool_calls_total:
        total = tool_calls_total[tool_name]
        successful = tool_calls_successful[tool_name]
        success_rates[tool_name] = (successful / total * 100) if total > 0 else 0.0
    
    # Get git metrics if we can find base commit
    git_metrics = get_git_metrics_from_session(events)
    
    # Get tool-specific line changes
    tool_metrics = calculate_tool_lines_changed(events)
    
    summary_data = {
        "total_duration_seconds": round(total_duration_seconds, 2),
        "assistant_turns": assistant_turns,
        "human_turns": human_turns,
        "tool_calls": {
            "successful": dict(tool_calls_successful),
            "failed": dict(tool_calls_failed),
            "success_rate": success_rates,
            "total_by_type": dict(tool_calls_total)
        },
        "usage_totals": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cache_creation_tokens": total_cache_creation_tokens,
            "total_cache_read_tokens": total_cache_read_tokens,
            "total_ephemeral_5m_tokens": total_ephemeral_5m_tokens,
            "total_ephemeral_1h_tokens": total_ephemeral_1h_tokens,
            "service_tier": service_tier,
            "total_cost": None
        }
    }
    
    # Add git metrics if available
    if git_metrics:
        summary_data.update(git_metrics)
    
    # Add tool metrics
    summary_data.update(tool_metrics)
    
    return summary_data

def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        # Extract relevant data
        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path", "")
        cwd = input_data.get("cwd", "")
        
        # Get correct log file path (routes to model-specific directory for A/B testing)
        log_file = get_log_file_path(session_id, cwd)
        
        # Analyze the session log
        summary_data = analyze_session_log(log_file)
        
        if summary_data is None:
            print("Warning: Could not analyze session log", file=sys.stderr)
            return
        
        # Check if raw transcript copy exists (in same directory as processed log)
        log_dir = os.path.dirname(log_file)
        raw_transcript_path = os.path.join(log_dir, f"session_{session_id}_raw.jsonl")
        raw_transcript_exists = os.path.exists(raw_transcript_path)
        
        # Create summary log entry
        log_entry = {
            "event_type": "session_summary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "transcript_path": transcript_path,
            "cwd": cwd,
            "content": {
                **summary_data,
                "files": {
                    "processed_log": f"session_{session_id}.jsonl",
                    "raw_transcript": f"session_{session_id}_raw.jsonl" if raw_transcript_exists else None,
                    "raw_transcript_source": transcript_path
                }
            }
        }
        
        # Add A/B testing metadata
        log_entry = add_ab_metadata_to_log_entry(log_entry, cwd)
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Append summary to session log file (JSONL format)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    except Exception as e:
        print(f"Error generating session summary: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

