"""docs/VALIDATION.md and the run records it cites agree: every record it links exists, and every run it reports is on file."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATION = ROOT / "docs" / "VALIDATION.md"
RUNS = ROOT / "docs" / "validation"


def test_every_record_validation_md_links_exists():
    text = VALIDATION.read_text(encoding="utf-8")
    links = re.findall(r"\]\((validation/[^)#]+)\)", text)
    assert links, "docs/VALIDATION.md links no run records"
    missing = [link for link in links if not (ROOT / "docs" / link).exists()]
    assert missing == []


def test_every_repository_in_a_run_has_its_three_outputs_and_its_commit_on_record():
    for run in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        selection = (run / "SELECTION.md").read_text(encoding="utf-8")
        taken = re.findall(r"taken: ([\w.-]+)/([\w.-]+) at ([0-9a-f]{40})", selection)
        assert len(taken) == 5, f"{run.name}: the selection should record five repositories taken"
        for _, repo, sha in taken:
            for command in ("check", "critic", "readme-critic"):
                record = run / f"{repo}.{command}.txt"
                assert record.exists(), f"{run.name}: no {record.name}"
                first = record.read_text(encoding="utf-8").splitlines()[0]
                assert sha[:12] in first, f"{record.name} does not name the commit {sha[:12]}"
                assert re.match(r"^exit \d+$", record.read_text(encoding="utf-8").splitlines()[1])
            assert sha[:7] in VALIDATION.read_text(encoding="utf-8"), f"docs/VALIDATION.md does not name {repo} at {sha[:7]}"
