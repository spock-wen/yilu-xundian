#!/usr/bin/env python3
"""Structural lint for the Keels 0.2.2 border/radius ordering bug in lib/index.cj.

`.border(width:, color:)` without a `radius:` argument resets the node's radius to 0,
so a `.borderRadius(N)` placed BEFORE `.border(...)` in the same modifier chain is
ineffective (square corners on device). This script splits index.cj into modifier
chains (maximal runs of consecutive lines starting with `.`), and flags any chain
where `.borderRadius(` precedes a `.border(` that carries no `radius:` argument.

Exit codes: 0 PASS, 1 any border/borderRadius ordering violation,
2 an enforced anchor is missing or its chain's radius is not 4.
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


def check_source(text, filename="index.cj", check_anchors=False, verbose=False):
    """Check text for border/borderRadius ordering violations.

    Returns (violations, enforced_ok, missing_anchors).
    """
    lines = text.splitlines()
    name = os.path.basename(filename)

    enforced_ok = 0
    violations = []
    anchor_seen = {a: False for a in ENFORCED_ANCHORS} if check_anchors else {}

    for start, chain in split_chains(lines):
        calls = chain_calls(chain)
        enforced = check_anchors and any(a in line for line in chain for a in ENFORCED_ANCHORS)
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
            msg = ("VIOLATION %s:%d radius=%s chain starts line %d: borderRadius before border"
                   % (name, radius_line, radius_val, start))
            violations.append(msg)
        else:
            if enforced:
                enforced_ok += 1
            if verbose:
                print("OK %s:%d radius=%s chain starts line %d"
                      % (name, radius_line, radius_val, start))

    missing = [a for a, seen in anchor_seen.items() if not seen] if check_anchors else []
    return violations, enforced_ok, missing


def run_selftest():
    bad_snippet = """
    Row()
        .borderRadius(8)
        .border(width: 1, color: Theme.accent)
    """
    good_snippet_after = """
    Row()
        .border(width: 1, color: Theme.accent)
        .borderRadius(8)
    """
    good_snippet_with_radius = """
    Row()
        .borderRadius(8)
        .border(width: 1, color: Theme.accent, radius: 8)
    """

    try:
        # 1. borderRadius before border (without radius:) must be caught
        v_bad, _, _ = check_source(bad_snippet, "test.cj", check_anchors=False)
        assert len(v_bad) == 1, f"Expected 1 violation in bad snippet, got {len(v_bad)}"
        assert "borderRadius before border" in v_bad[0], f"Unexpected violation message: {v_bad[0]}"

        # 2. borderRadius after border must pass
        v_good1, _, _ = check_source(good_snippet_after, "test.cj", check_anchors=False)
        assert len(v_good1) == 0, f"Expected 0 violations in good snippet (after), got {len(v_good1)}"

        # 3. .border(..., radius: 8) with radius parameter must pass
        v_good2, _, _ = check_source(good_snippet_with_radius, "test.cj", check_anchors=False)
        assert len(v_good2) == 0, f"Expected 0 violations in good snippet (with radius:), got {len(v_good2)}"

        # 4. Combined good snippet must also pass
        good_combined = good_snippet_after + "\n" + good_snippet_with_radius
        v_comb, _, _ = check_source(good_combined, "test.cj", check_anchors=False)
        assert len(v_comb) == 0, f"Expected 0 violations in combined good snippets, got {len(v_comb)}"
    except AssertionError as e:
        print("selftest FAIL: %s" % e, file=sys.stderr)
        sys.exit(1)

    print("selftest OK")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", default=DEFAULT_LIB,
                    help="index.cj to lint (default: ../lib/index.cj)")
    ap.add_argument("--strict", action="store_true",
                    help="fail on violations in non-enforced chains too (retained for compatibility)")
    ap.add_argument("--verbose", action="store_true",
                    help="also print OK lines for correct chains")
    ap.add_argument("--selftest", action="store_true",
                    help="run self-test assertions on in-memory code snippets")
    args = ap.parse_args()

    if args.selftest:
        run_selftest()

    text = open(args.path, encoding="utf-8").read()
    violations, enforced_ok, missing = check_source(
        text, filename=args.path, check_anchors=True, verbose=args.verbose
    )

    for v in violations:
        print(v)

    if missing:
        print("FAIL: anchor missing or radius!=4: %s" % "; ".join(missing))
        sys.exit(2)
    if violations:
        print("check_border_radius: FAIL (%d violations)" % len(violations))
        sys.exit(1)
    print("check_border_radius: PASS (%d enforced chains ok, 0 violations)"
          % enforced_ok)


if __name__ == "__main__":
    main()
