#!/usr/bin/env python3
"""
Ralph loop Stop hook — blocks agent exit if loop is active and no completion promise found.

State file: {cwd}/.claude/ralph-loop.local.md (YAML frontmatter + prompt body)
Exit codes: 0 = allow exit, 2 = block exit (continue loop)
"""

import json
import os
import re
import sys
from pathlib import Path


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter without PyYAML dependency."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    config = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        # Parse simple types
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        else:
            try:
                value = int(value)
            except ValueError:
                pass
        config[key.strip()] = value
    return config


def update_iteration(state_path: Path, config: dict, content: str):
    """Increment iteration counter in state file."""
    old_iter = f"iteration: {config['iteration']}"
    new_iter = f"iteration: {config['iteration'] + 1}"
    state_path.write_text(content.replace(old_iter, new_iter, 1))


def check_promise_in_transcript(transcript_path: str, promise: str) -> bool:
    """Check if completion promise appears in recent transcript entries."""
    if not transcript_path:
        return False

    path = Path(transcript_path)
    if not path.exists():
        return False

    try:
        # Read last 20KB of transcript (enough for recent entries)
        size = path.stat().st_size
        with open(path, "r") as f:
            if size > 20_000:
                f.seek(size - 20_000)
                f.readline()  # Skip partial line
            tail = f.read()
    except OSError:
        return False

    # Search for <promise>TEXT</promise> in transcript
    pattern = f"<promise>{re.escape(promise)}</promise>"
    return bool(re.search(pattern, tail))


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # Determine working directory
    cwd = data.get("cwd") or os.getcwd()
    state_path = Path(cwd) / ".claude" / "ralph-loop.local.md"

    if not state_path.exists():
        sys.exit(0)

    content = state_path.read_text()
    config = parse_frontmatter(content)

    if not config.get("active", False):
        sys.exit(0)

    iteration = config.get("iteration", 1)
    max_iterations = config.get("max_iterations", 10)
    promise = config.get("completion_promise", "")

    # Max iterations reached — allow exit, cleanup
    if iteration >= max_iterations:
        state_path.unlink(missing_ok=True)
        print(f"Ralph loop: max iterations ({max_iterations}) reached. Stopping.", file=sys.stderr)
        sys.exit(0)

    # Check for completion promise in transcript
    transcript_path = data.get("transcript_path", "")
    if promise and check_promise_in_transcript(transcript_path, promise):
        state_path.unlink(missing_ok=True)
        print(f"Ralph loop: completion promise found. Done.", file=sys.stderr)
        sys.exit(0)

    # No promise, iterations remain — block exit, increment counter
    update_iteration(state_path, config, content)
    print(f"Ralph loop: iteration {iteration}/{max_iterations}, continuing...", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
