---
name: cancel-ralph
description: >
  Cancel an active ralph loop. Removes state file and allows agent to stop.
  Triggers: "cancel-ralph", "/cancel-ralph", "stop ralph", "отмени ральфа"
allowed-tools: [Bash]
---

# Cancel Ralph Loop

```bash
rm -f .claude/ralph-loop.local.md
```

Output: "Ralph loop cancelled."
