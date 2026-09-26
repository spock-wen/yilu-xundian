#!/usr/bin/env python3
"""SKILL.md doctor claims must match cmd_doctor.

The allowlist is parsed from executable source of ``cmd_doctor`` and ``hdc``
(comments stripped). It is not a second handwritten checklist.

Empty extracted claims fail. Claims that name a check the source does not
implement fail (claim-diff). Numbered ``## Doctor`` items that match no known
check fail closed so a new aspirational bullet cannot pass silently.

Run:

    python3 tools/verify/test_skill_doctor_contract.py
    python3 -m unittest discover -s tools/verify -p 'test_skill_doctor_contract.py' -t tools/verify
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import control_yilu  # noqa: E402

SKILL_PATH = (
    control_yilu.ROOT / ".cursor" / "skills" / "verify-yilu-xundian" / "SKILL.md"
)

# Phrase → check id. Positive wording only; negation clauses are dropped first.
CLAIM_RES: list[tuple[str, re.Pattern[str]]] = [
    (
        "ability_process",
        re.compile(
            r"ability process|process-level ability|process probe|"
            r"reports the ability|running ability|ability is running|\bpidof\b",
            re.I,
        ),
    ),
    (
        "hap_mtime",
        re.compile(r"HAP mtime|stat(?:s|ting)?(?:\s+a)?\s+HAP|\.hap\b", re.I),
    ),
    (
        "hdc_on_path",
        re.compile(r"hdc(?:`|')?\s+is on PATH|hdc on PATH|hdc not on PATH", re.I),
    ),
    (
        "target_listed",
        re.compile(r"list targets|target listed|contains the target", re.I),
    ),
    (
        "bundle_installed",
        re.compile(r"\bbm dump\b|bundle installed|shows the bundle", re.I),
    ),
    (
        "rules",
        re.compile(r"test_rules\.py|rules green", re.I),
    ),
    (
        "git_sha_print",
        re.compile(
            r"short SHA|git\s+`?HEAD`?|git rev-parse --short",
            re.I,
        ),
    ),
]

_NEG_SPLIT = re.compile(
    r"\b(?:does not|do not|doesn't|don't|never)\b|并不|不会|不检查|不探测",
    re.I,
)

# Historical false claim (SKILL before 45eae59) plus the real check list.
FALSE_ABILITY_SKILL = """\
# Verify

Ready when `doctor` reports the ability process and a fresh screenshot can be taken.

## Doctor

Checks (read-only):

1. `hdc` is on PATH. If the binary is missing, doctor exits 1 and prints `FAIL: hdc not on PATH`.
2. `hdc -t "$YILU_HDC_TARGET" list targets` contains the target.
3. `bm dump -n com.yilu.xundian` shows the bundle.
4. From repo root, `python3 tools/test_rules.py` exit 0 (rules green).
5. Prints the git `HEAD` short SHA (`git rev-parse --short HEAD`) on the doctor log line.

## Drive
"""

EMPTY_DOCTOR_SKILL = """\
# Verify

## Doctor

```bash
python3 tools/verify/control_yilu.py doctor
```

## Drive
"""

PROCESS_PROBE_DOCTOR = '''\
def cmd_doctor(_: argparse.Namespace) -> int:
    listed = hdc("list", "targets", check=False)
    hdc_shell("pidof com.yilu.xundian", check=False)
    return 0
'''


def strip_comments(src: str) -> str:
    out: list[str] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(src).readline)
    except tokenize.TokenError:
        return src
    for tok in tokens:
        if tok.type in (tokenize.COMMENT, tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        if tok.type in (tokenize.NL, tokenize.NEWLINE):
            out.append("\n")
            continue
        if tok.type == tokenize.DEDENT:
            continue
        out.append(tok.string)
        if tok.type not in (tokenize.INDENT, tokenize.NEWLINE, tokenize.NL):
            out.append(" ")
    return "".join(out)


def function_source(src: str, name: str) -> str:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            seg = ast.get_source_segment(src, node)
            if seg:
                return seg
    raise AssertionError(f"function {name} not found")


def implemented_checks(doctor_exec: str, hdc_exec: str) -> set[str]:
    """Checks visible in executable doctor/hdc source. Comments do not count."""
    found: set[str] = set()
    if (
        re.search(r"\bhdc\s*\(", doctor_exec)
        and "FileNotFoundError" in hdc_exec
        and "not on PATH" in hdc_exec
    ):
        found.add("hdc_on_path")
    if re.search(r"""['"]list['"]\s*,\s*['"]targets['"]""", doctor_exec) or (
        "list targets" in doctor_exec
    ):
        found.add("target_listed")
    if "bm dump" in doctor_exec and re.search(r"\bBUNDLE\b", doctor_exec):
        found.add("bundle_installed")
    if "test_rules.py" in doctor_exec:
        found.add("rules")
    if re.search(r"\bgit_sha\s*\(", doctor_exec):
        found.add("git_sha_print")
    # subprocess must not count as a process-level ability probe.
    if re.search(
        r"\bpidof\b|\bps\s+-|hidumper|ability process|\baa\s+dump\b",
        doctor_exec,
    ):
        found.add("ability_process")
    if re.search(r"\.hap\b|st_mtime|HAP mtime", doctor_exec):
        found.add("hap_mtime")
    return found


def harness_sources() -> tuple[str, str]:
    src = Path(control_yilu.__file__).read_text(encoding="utf-8")
    doctor = strip_comments(function_source(src, "cmd_doctor"))
    hdc = strip_comments(function_source(src, "hdc"))
    return doctor, hdc


def implemented_checks_from_harness() -> set[str]:
    doctor, hdc = harness_sources()
    return implemented_checks(doctor, hdc)


def doctor_section(skill: str) -> str:
    match = re.search(r"^## Doctor\s*$", skill, re.M)
    if not match:
        return ""
    rest = skill[match.end() :]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _sentences(text: str) -> list[str]:
    parts = re.split(r"\n+", text)
    out: list[str] = []
    for part in parts:
        out.extend(p.strip() for p in re.split(r"(?<=[。.!?])\s+", part) if p.strip())
    return out


def claims_in(text: str) -> set[str]:
    found: set[str] = set()
    for sent in _sentences(text):
        positive = _NEG_SPLIT.split(sent, maxsplit=1)[0]
        for cid, cre in CLAIM_RES:
            if cre.search(positive):
                found.add(cid)
    return found


def numbered_items(section: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        if re.match(r"\s*\d+\.\s+", line):
            if current:
                items.append("\n".join(current))
            current = [line]
        elif current and line.strip():
            current.append(line)
        elif current and not line.strip():
            items.append("\n".join(current))
            current = []
    if current:
        items.append("\n".join(current))
    return items


def extract_claims(skill: str) -> tuple[set[str], list[str]]:
    """Return (claim ids, unrecognized numbered doctor items)."""
    section = doctor_section(skill)
    claims = claims_in(section)
    unknown: list[str] = []
    for item in numbered_items(section):
        if not claims_in(item):
            unknown.append(" ".join(item.split()))
    for sent in _sentences(skill):
        if re.search(r"\bdoctor\b", sent, re.I):
            claims |= claims_in(sent)
    return claims, unknown


def contract_errors(skill: str, implemented: set[str]) -> list[str]:
    section = doctor_section(skill)
    section_claims = claims_in(section)
    claims, unknown = extract_claims(skill)
    errors: list[str] = []
    if not section.strip() or not section_claims:
        errors.append(
            "empty claim-diff: ## Doctor section asserts no implemented checks"
        )
    if not claims:
        errors.append("empty claim-diff: no doctor checks extracted from SKILL.md")
    for item in unknown:
        errors.append(f"mismatched claim-diff: unrecognized doctor check: {item}")
    unsupported = claims - implemented
    missing = implemented - claims
    if unsupported or missing:
        errors.append(
            "mismatched claim-diff: "
            f"unsupported={sorted(unsupported)} missing={sorted(missing)}"
        )
    return errors


class SkillDoctorContractTest(unittest.TestCase):
    def test_live_skill_matches_doctor_source(self) -> None:
        skill = SKILL_PATH.read_text(encoding="utf-8")
        impl = implemented_checks_from_harness()
        errors = contract_errors(skill, impl)
        self.assertEqual(errors, [], "\n".join(errors))
        self.assertNotIn("ability_process", impl)
        self.assertNotIn("hap_mtime", impl)
        self.assertGreaterEqual(len(impl), 4)

    def test_ability_process_claim_fails(self) -> None:
        impl = implemented_checks_from_harness()
        self.assertNotIn("ability_process", impl)
        errors = contract_errors(FALSE_ABILITY_SKILL, impl)
        blob = "\n".join(errors)
        self.assertIn("mismatched claim-diff", blob)
        self.assertIn("ability_process", blob)
        self.assertTrue(any(e.startswith("mismatched claim-diff: unsupported=") for e in errors))

    def test_empty_doctor_section_fails_even_if_implementation_empty(self) -> None:
        errors = contract_errors(EMPTY_DOCTOR_SKILL, set())
        self.assertTrue(errors)
        self.assertTrue(any(e.startswith("empty claim-diff:") for e in errors))

    def test_empty_claims_against_real_doctor_fail(self) -> None:
        impl = implemented_checks_from_harness()
        errors = contract_errors(EMPTY_DOCTOR_SKILL, impl)
        blob = "\n".join(errors)
        self.assertIn("empty claim-diff", blob)
        self.assertIn("mismatched claim-diff", blob)
        self.assertIn("missing=", blob)

    def test_allowlist_follows_doctor_source(self) -> None:
        """A pidof probe in doctor source becomes an implemented check."""
        hdc_exec = strip_comments(function_source(
            Path(control_yilu.__file__).read_text(encoding="utf-8"), "hdc"
        ))
        bare = implemented_checks(PROCESS_PROBE_DOCTOR, hdc_exec)
        self.assertIn("ability_process", bare)
        self.assertIn("target_listed", bare)
        self.assertNotIn("rules", bare)
        skill = SKILL_PATH.read_text(encoding="utf-8")
        errors = contract_errors(skill, bare)
        blob = "\n".join(errors)
        self.assertIn("mismatched claim-diff", blob)
        self.assertIn("ability_process", blob)

    def test_comment_only_aa_dump_is_not_an_ability_probe(self) -> None:
        doctor, _hdc = harness_sources()
        self.assertNotIn("aa dump", doctor)
        self.assertNotIn("ability_process", implemented_checks_from_harness())


def main() -> int:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    impl = implemented_checks_from_harness()
    live = contract_errors(skill, impl)
    false_errors = contract_errors(FALSE_ABILITY_SKILL, impl)
    empty_errors = contract_errors(EMPTY_DOCTOR_SKILL, impl)

    print(f"implemented={sorted(impl)}")
    if live:
        print("live SKILL+doctor: FAIL")
        for err in live:
            print(f"  {err}")
    else:
        print("live SKILL+doctor: PASS")

    false_hit = any("ability_process" in err for err in false_errors)
    print(
        "fixture ability-process claim: "
        + (
            "FAIL (expected) " + next(e for e in false_errors if "ability_process" in e)
            if false_hit
            else "PASS (unexpected — false claim was accepted)"
        )
    )
    empty_hit = any(e.startswith("empty claim-diff:") for e in empty_errors)
    print(
        "fixture empty doctor section: "
        + (
            "FAIL (expected) " + next(e for e in empty_errors if e.startswith("empty claim-diff:"))
            if empty_hit
            else "PASS (unexpected — empty claims were accepted)"
        )
    )

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SkillDoctorContractTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    ok = result.wasSuccessful() and not live and false_hit and empty_hit
    print("SKILL↔doctor contract PASS" if ok else "SKILL↔doctor contract FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
