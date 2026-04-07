#!/usr/bin/env python3
"""Superset check: all backup lines must exist in sorted. New lines (added headers) are OK."""
import sys
from collections import Counter


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <backup> <sorted>")
        sys.exit(2)
    with open(sys.argv[1]) as f:
        bak = [l.rstrip() for l in f if l.strip()]
    with open(sys.argv[2]) as f:
        new = [l.rstrip() for l in f if l.strip()]
    bak_c, new_c = Counter(bak), Counter(new)
    missing = bak_c - new_c  # lines in backup not found in sorted
    extra = new_c - bak_c    # new lines in sorted (added headers etc.)
    if not missing:
        extra_count = sum(extra.values())
        msg = f"✅ VERIFIED: all {len(bak)} original lines preserved"
        if extra_count:
            msg += f" (+{extra_count} new lines added)"
        print(msg)
        sys.exit(0)
    print(f"❌ MISSING ({sum(missing.values())}):")
    for l, c in sorted(missing.items(), key=lambda x: -x[1]):
        print(f"  [{c}x] «{l[:120]}»")
    if extra:
        print(f"ℹ️  ADDED ({sum(extra.values())} new lines — OK)")
    sys.exit(1)


if __name__ == "__main__":
    main()
