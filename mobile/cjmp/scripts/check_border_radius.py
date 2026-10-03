#!/usr/bin/env python3
"""Structural lint for the Keels 0.2.2 border/radius ordering bug in lib/index.cj.

`.border(width:, color:)` without a `radius:` argument resets the node's radius to 0,
so a `.borderRadius(N)` placed BEFORE `.border(...)` in the same modifier chain is
ineffective (square corners on device). This script splits index.cj into modifier
chains (maximal runs of consecutive lines starting with `.`), and flags any chain
where `.borderRadius(` precedes a `.border(` that carries no `radius:` argument.

Exit codes: 0 PASS, 1 violation in an enforced chain (or any violation with
--strict), 2 an enforced anchor is missing or its chain's radius is not 4.
"""
import argparse
import os
import re
import sys

CJMP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LIB = os.path.join(CJMP, "lib", "index.cj")

# Chains carrying any of these anchors are the chip chains this lint enforces.
ENFORCED_ANCHORS = [
    "this.stepChipBorder()",
    "this.stepLeftBorderColor()",
    "border(width: 1, color: Theme.paperLine)",
]

BORDER_RE = re.compile(r"\.border\s*\(")          # matches .border( only, not .borderRadius( etc.
RADIUS_RE = re.compile(r"\.borderRadius\s*\(")
RADIUS_VAL_RE = re.compile(r"\.borderRadius\s*\(\s*(\d+)")


def split_chains(lines):
    """Yield (first_lineno_1based, [lines]) for each maximal run of `.`-prefixed lines."""
    chain = []
    start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("."):
            if not chain:
                start = i
            chain.append(line)
        elif chain:
            yield start + 1, chain
            chain = []
    if chain:
        yield start + 1, chain


def chain_calls(chain):
    """(border_idx, radius_idx, radius_val) within the chain, or None if not both present."""
    border_idx = radius_idx = None
    radius_val = None
    for idx, line in enumerate(chain):
        if radius_idx is None and RADIUS_RE.search(line):
            radius_idx = idx
            m = RADIUS_VAL_RE.search(line)
            radius_val = int(m.group(1)) if m else None
        # only a .border( with no radius: argument resets the radius to 0
        if border_idx is None and BORDER_RE.search(line) and "radius:" not in line:
            border_idx = idx
    if border_idx is None or radius_idx is None:
        return None
    return border_idx, radius_idx, radius_val


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", default=DEFAULT_LIB,
                    help="index.cj to lint (default: ../lib/index.cj)")
    ap.add_argument("--strict", action="store_true",
                    help="fail on violations in non-enforced chains too")
    ap.add_argument("--verbose", action="store_true",
                    help="also print OK lines for correct chains")
    args = ap.parse_args()

    text = open(args.path, encoding="utf-8").read()
    lines = text.splitlines()
    name = os.path.basename(args.path)

    enforced_ok = 0
    warnings = 0
    failures = 0
    anchor_seen = {a: False for a in ENFORCED_ANCHORS}

    for start, chain in split_chains(lines):
        calls = chain_calls(chain)
        enforced = any(a in line for line in chain for a in ENFORCED_ANCHORS)
        if enforced:
            for a in ENFORCED_ANCHORS:
                if any(a in line for line in chain) and calls is not None:
                    # anchor counts only if its chain has both calls and radius 4
                    if calls[2] == 4:
                        anchor_seen[a] = True
        if calls is None:
            continue
        border_idx, radius_idx, radius_val = calls
        radius_line = start + radius_idx
        if radius_idx < border_idx:
            msg = ("VIOLATION %s:%d radius=%s chain starts line %d"
                   % (name, radius_line, radius_val, start))
            if enforced:
                print("FAIL: chip chain %s:%d borderRadius before border (%s)"
                      % (name, radius_line, msg))
                failures += 1
            elif args.strict:
                print(msg)
                failures += 1
            else:
                print("%s WARN known-unfixed" % msg)
                warnings += 1
        else:
            if enforced:
                enforced_ok += 1
            if args.verbose:
                print("OK %s:%d radius=%s chain starts line %d"
                      % (name, radius_line, radius_val, start))

    missing = [a for a, seen in anchor_seen.items() if not seen]
    if missing:
        print("FAIL: anchor missing or radius!=4: %s" % "; ".join(missing))
        sys.exit(2)
    if failures:
        print("check_border_radius: FAIL (%d failures, %d warnings)" % (failures, warnings))
        sys.exit(1)
    print("check_border_radius: PASS (%d enforced chains ok, %d warnings)"
          % (enforced_ok, warnings))


if __name__ == "__main__":
    main()
