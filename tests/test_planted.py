"""The planted-defect collection: small repositories with known defects, scored against an answer key.

Each file in `tests/planted/` is one small repository written out as text: a header (the answer key) and then the files,
each after a line `=== file: <path>`. The test unpacks it into a scratch folder, runs the claims critic over it with the
suite result the header gives (Burnish counts no tests, so the key says what a run measured), and compares what the critic
flags with the key.

A FLAG is a row of the critic's report that is not supported, identified by the file and line it points at and its kind.
For each repository:

  * a CATCH is a key line the critic flags with the right kind,
  * a MISS is a key line it does not flag,
  * a FALSE ALARM is a flag the key does not list as a defect.

The key records today's result too: a defect the critic does not catch yet is written `defect: ... missed`, and a flag on a
line that holds no defect is written `false-alarm: ...`. The test fails when the result differs from the key in either
direction. Worse (a catch lost, a new false alarm) is a regression. Better (a miss caught, a false alarm gone) must be
written into the key, so an improvement is on the record in the change that makes it. `docs/PLANTED.md` holds the totals.

Header lines:

    about: one sentence on what the repository plants
    group: catch | trap | hard
    suite: passed=N [failed=N] [errors=N] [skipped=N]
    defect: <file>:<line> <kind> [missed]
    false-alarm: <file>:<line> <kind>

Line 0 means the whole file. The file "-" means a finding about the run rather than a place in a file, such as a suite that
is not green.

Groups: "catch" plants defects the critic should catch, "trap" plants honest sentences that look like defects (it may hold no
defect), and "hard" plants defects and traps where claim reading is hard (tables, headings, quotes, negation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from cns.seat import Facts
from cns.suite import SuiteRun

from burnish.critic import PoetryCritic

PLANTED = Path(__file__).parent / "planted"
LEDGER = Path(__file__).resolve().parents[1] / "docs" / "PLANTED.md"
GROUPS = ("catch", "trap", "hard")
KINDS = frozenset({"tests", "pin", "dependencies", "absolute", "metadata", "readme-shape", "history", "parse", "suite"})

Flag = tuple[str, int, str]   # (file, line, kind)

_FILE = re.compile(r"^=== file: (\S+)\s*$")
_ENTRY = re.compile(r"^(?P<path>[\w./-]+|-):(?P<line>\d+)\s+(?P<kind>[\w-]+)(?:\s+(?P<missed>missed))?\s*$")


@dataclass
class Planted:
    """One planted repository: its answer key and its files."""

    name: str
    about: str = ""
    group: str = ""
    suite: dict[str, int] = field(default_factory=dict)
    defects: set[Flag] = field(default_factory=set)
    missed: set[Flag] = field(default_factory=set)
    alarms: set[Flag] = field(default_factory=set)
    files: dict[str, str] = field(default_factory=dict)


def _entry(name: str, raw: str, allow_missed: bool) -> tuple[Flag, bool]:
    match = _ENTRY.match(raw)
    assert match, f"{name}: cannot read the key entry {raw!r}"
    assert match["kind"] in KINDS, f"{name}: unknown kind {match['kind']!r}"
    assert allow_missed or not match["missed"], f"{name}: only a defect can be marked missed: {raw!r}"
    return (match["path"], int(match["line"]), match["kind"]), bool(match["missed"])


def load(path: Path) -> Planted:
    """Read one planted repository from its text file."""
    planted = Planted(path.stem)
    current: str | None = None
    body: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        opened = _FILE.match(line)
        if opened:
            if current is not None:
                planted.files[current] = "".join(body)
            current, body = opened.group(1), []
        elif current is not None:
            body.append(line)
        elif line.strip() and not line.startswith("#"):
            key, _, value = line.partition(":")
            value = value.strip()
            if key == "about":
                planted.about = value
            elif key == "group":
                planted.group = value
            elif key == "suite":
                planted.suite = {k: int(v) for k, v in (part.split("=") for part in value.split())}
            elif key == "defect":
                flag, missed = _entry(planted.name, value, allow_missed=True)
                planted.defects.add(flag)
                if missed:
                    planted.missed.add(flag)
            elif key == "false-alarm":
                planted.alarms.add(_entry(planted.name, value, allow_missed=False)[0])
            else:
                raise AssertionError(f"{planted.name}: unknown header line {line.strip()!r}")
    if current is not None:
        planted.files[current] = "".join(body)
    return planted


def collection() -> list[Planted]:
    return [load(path) for path in sorted(PLANTED.glob("*.txt"))]


def flags(planted: Planted, scratch: Path) -> set[Flag]:
    """Unpack the repository into `scratch`, run the critic over it, and return every unsupported row as a flag."""
    for relative, text in planted.files.items():
        target = scratch / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    given = planted.suite or {"passed": 10}
    unknown = set(given) - {"passed", "failed", "errors", "skipped"}
    assert not unknown, f"{planted.name}: unknown suite field(s) {sorted(unknown)}"
    suite = SuiteRun(ran=True, passed=given.get("passed", 0), failed=given.get("failed", 0), errors=given.get("errors", 0),
                     skipped=given.get("skipped", 0))
    report = PoetryCritic().critique(scratch, facts=Facts(suite=suite, remaining=(), cycles=1))
    out: set[Flag] = set()
    for row in report.claims:
        if row.supported:
            continue
        assert row.provenance is not None, f"{planted.name}: a row with no provenance"
        at = row.provenance.claim_at
        out.add((at.path or "-", at.line, row.kind))
    return out


@dataclass(frozen=True)
class Score:
    """One repository's result: what was caught, missed and wrongly flagged."""

    caught: frozenset[Flag]
    missed: frozenset[Flag]
    alarms: frozenset[Flag]


def score(planted: Planted, found: set[Flag]) -> Score:
    return Score(frozenset(planted.defects & found), frozenset(planted.defects - found), frozenset(found - planted.defects))


def _show(items: frozenset[Flag] | set[Flag]) -> str:
    return ", ".join(f"{path}:{line} {kind}" for path, line, kind in sorted(items)) or "none"


# ------------------------------------------------------------------ the key is well formed


def test_the_collection_has_every_group():
    planted = collection()
    assert planted, "tests/planted/ holds no planted repositories"
    for group in GROUPS:
        assert any(p.group == group for p in planted), f"no planted repository in group {group!r}"


@pytest.mark.parametrize("planted", collection(), ids=lambda p: p.name)
def test_every_answer_key_is_well_formed(planted: Planted):
    assert planted.about, f"{planted.name}: no 'about' line"
    assert planted.group in GROUPS, f"{planted.name}: group must be one of {GROUPS}"
    assert "README.md" in planted.files, f"{planted.name}: no README.md"
    if planted.group == "trap":
        assert not planted.defects, f"{planted.name}: a trap plants no defect"
    if planted.group == "catch":
        assert planted.defects, f"{planted.name}: a catch repository plants at least one defect"
    assert not planted.defects & planted.alarms, f"{planted.name}: a line cannot be both a defect and a false alarm"
    for path, line, _ in planted.defects | planted.alarms:
        if path == "-":   # a finding about the run, not a place in a file (a suite that is not green)
            continue
        assert path in planted.files, f"{planted.name}: the key points at {path}, which is not in the repository"
        if line:
            lines = planted.files[path].splitlines()
            assert line <= len(lines) and lines[line - 1].strip(), f"{planted.name}: {path}:{line} is blank or past the end"


# ------------------------------------------------------------------ the critic against the key


@pytest.mark.parametrize("planted", collection(), ids=lambda p: p.name)
def test_the_critic_scores_as_the_key_records(planted: Planted, tmp_path: Path):
    """Catches, misses and false alarms match the key exactly. A difference is a regression, or an improvement to record."""
    result = score(planted, flags(planted, tmp_path))
    expected_missed = frozenset(planted.missed)
    expected_alarms = frozenset(planted.alarms)
    problems = []
    if lost := result.missed - expected_missed:
        problems.append(f"worse: no longer caught: {_show(lost)}")
    if new := result.alarms - expected_alarms:
        problems.append(f"worse: new false alarm: {_show(new)}")
    if gained := expected_missed - result.missed:
        problems.append(f"better: now caught, remove 'missed' from the key: {_show(gained)}")
    if gone := expected_alarms - result.alarms:
        problems.append(f"better: false alarm gone, remove it from the key: {_show(gone)}")
    assert not problems, f"{planted.name} ({planted.about}):\n  " + "\n  ".join(problems)


def scorecard() -> dict[str, tuple[int, int, int]]:
    """(catches, misses, false alarms) per group and in total, as the key records them."""
    totals = {group: [0, 0, 0] for group in (*GROUPS, "total")}
    for planted in collection():
        caught = len(planted.defects - planted.missed)
        for group in (planted.group, "total"):
            totals[group][0] += caught
            totals[group][1] += len(planted.missed)
            totals[group][2] += len(planted.alarms)
    return {group: (c, m, a) for group, (c, m, a) in totals.items()}


def test_docs_planted_states_the_scorecard_the_key_records():
    """The totals table in docs/PLANTED.md is the key's own totals, so a change to the key changes the document with it."""
    text = LEDGER.read_text(encoding="utf-8")
    for group, (caught, missed, alarms) in scorecard().items():
        repos = sum(1 for p in collection() if p.group == group) if group != "total" else len(collection())
        row = f"| {group} | {repos} | {caught} | {missed} | {alarms} |"
        assert row in text, f"docs/PLANTED.md should have the row {row!r}"
