"""Streamline as Elegant's craft, run through Elegant's real tag team."""

from pathlib import Path

from elegant.authorization import grant
from elegant.tagteam import TagTeam

from streamline.craft import Streamline


def _tree(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text('"""demo package."""\n', encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text(
        "def test_a():\n    assert True\n\ndef test_b():\n    assert True\n", encoding="utf-8")
    (root / "PROVENANCE.md").write_text("All 16 tests passed unmodified on the system python3.\n", encoding="utf-8")
    (root / "README.md").write_text("# demo\n\nSee provenance.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndescription = "demo"\n', encoding="utf-8")


def _auth(root: Path):
    return grant("william", "transform", str(root.resolve()), "documentation", "test")


FINDINGS = [{"id": "ghost-abc", "detector": "doc_test_count_drift", "severity": "minor", "status": "confirmed",
             "summary": "PROVENANCE.md claims 16 test(s)", "evidence": {"file": "PROVENANCE.md"}}]


def test_without_a_grant_the_proposal_stands_and_nothing_is_written(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(craft=Streamline()).run(tmp_path, findings=FINDINGS, authorization=None)
    assert result.decision == "REFUSED" and not result.applied
    assert "All 16 tests passed" in (tmp_path / "PROVENANCE.md").read_text(encoding="utf-8")
    assert result.proposal is not None and result.proposal.edits


def test_an_authorized_rewrite_survives_the_independent_oracle(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(craft=Streamline()).run(tmp_path, findings=FINDINGS, authorization=_auth(tmp_path))
    text = (tmp_path / "PROVENANCE.md").read_text(encoding="utf-8")
    assert result.applied and result.attack.judgement == "ACCEPT"
    assert "16" in text and "All 16 tests passed unmodified" not in text
    assert '"""demo package."""' in (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8")
    assert result.suite_before.green and result.suite_after.green


def test_the_rewrite_is_one_clean_sentence(tmp_path: Path):
    _tree(tmp_path)
    TagTeam(craft=Streamline()).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    text = (tmp_path / "PROVENANCE.md").read_text(encoding="utf-8")
    assert text == "The tree contains 2 `test_*` functions (an earlier version of this document gave 16).\n"


def test_a_red_suite_stops_the_craft_before_it_writes(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "tests" / "test_x.py").write_text("def test_a():\n    assert False\n", encoding="utf-8")
    before = (tmp_path / "PROVENANCE.md").read_text(encoding="utf-8")
    result = TagTeam(craft=Streamline()).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "INCONCLUSIVE" and not result.applied
    assert (tmp_path / "PROVENANCE.md").read_text(encoding="utf-8") == before


def test_the_craft_is_loadable_by_the_name_elegant_documents():
    from elegant.cli import _load_craft
    assert isinstance(_load_craft("streamline.craft:Streamline"), Streamline)
