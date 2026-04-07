#!/usr/bin/env python3
"""Verify enriched spec format: tasks have AC, proof commands, files, leverage, required sections."""
import sys
import re


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <spec-file>")
        sys.exit(2)

    with open(sys.argv[1]) as f:
        content = f.read()
        lines = content.splitlines()

    errors = []
    is_product = bool(re.search(r'## User Stories|FR-\d{3}', content))

    # Required sections (all spec types)
    for section in ["## Overview", "## Constraints", "## Tasks", "## Execution Order"]:
        if section not in content:
            errors.append(f"Missing section: {section}")

    # Product-only sections
    if is_product:
        if "## User Stories" not in content:
            errors.append("Product spec missing: ## User Stories")

    # No unresolved clarification markers
    for i, line in enumerate(lines, 1):
        if "[NEEDS CLARIFICATION]" in line:
            errors.append(f"Line {i}: unresolved [NEEDS CLARIFICATION]: {line.strip()[:80]}")

    # Find all TASK blocks and validate each
    task_pattern = re.compile(r'^### TASK-(\d+)')
    task_starts = []
    for i, line in enumerate(lines):
        m = task_pattern.match(line)
        if m:
            task_starts.append((i, m.group(0)))

    if not task_starts:
        errors.append("No ### TASK-{N} blocks found")

    for idx, (start_line, task_id) in enumerate(task_starts):
        # Determine block end
        end_line = task_starts[idx + 1][0] if idx + 1 < len(task_starts) else len(lines)
        block = "\n".join(lines[start_line:end_line])

        # Files field
        if "**Files**:" not in block and "**Files:**" not in block:
            errors.append(f"{task_id} (line {start_line + 1}): missing **Files:** field")

        # Leverage field
        if "**Leverage**:" not in block and "**Leverage:**" not in block:
            errors.append(f"{task_id} (line {start_line + 1}): missing **Leverage:** field")

        # Acceptance Criteria
        has_ac = bool(re.search(r'\*\*Acceptance Criteria\*\*:|AC-\d|^\*\*AC\*\*:', block, re.MULTILINE))
        if not has_ac and "**AC**:" not in block:
            errors.append(f"{task_id} (line {start_line + 1}): missing Acceptance Criteria")

        # Proof field in AC
        if has_ac and "Proof:" not in block and "Proof: " not in block:
            errors.append(f"{task_id} (line {start_line + 1}): AC exists but no Proof: field")

        # Product-only: Requirements field
        if is_product and "**Requirements**:" not in block and "**Requirements:**" not in block:
            errors.append(f"{task_id} (line {start_line + 1}): product spec missing **Requirements:** field")

    # Validate Execution Order references all tasks
    exec_order_match = re.search(r'## Execution Order\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if exec_order_match:
        exec_order_text = exec_order_match.group(1)
        for _, task_id in task_starts:
            task_num = re.search(r'TASK-(\d+)', task_id).group(0)
            if task_num not in exec_order_text:
                errors.append(f"{task_num} not referenced in Execution Order")

        # Check [P] marker consistency between task header and execution order
        for start_line, task_id in task_starts:
            task_header_line = lines[start_line]
            has_p_in_header = '[P]' in task_header_line
            task_num = re.search(r'TASK-(\d+)', task_id).group(0)
            has_p_in_order = bool(re.search(rf'{task_num}\s*\[P\]', exec_order_text))
            if has_p_in_header != has_p_in_order:
                errors.append(f"{task_num}: [P] marker mismatch between task header and Execution Order")

    if not errors:
        task_count = len(task_starts)
        print(f"PASS: {task_count} tasks verified, all fields present" +
              (f" (product mode)" if is_product else " (technical/small mode)"))
        sys.exit(0)
    else:
        print(f"FAIL: {len(errors)} issues found:\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
