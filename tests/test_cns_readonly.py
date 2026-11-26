"""CNS analysis never writes, and CNS itself is NO_ACTION."""

from pathlib import Path

from burnish.cns_boundary import CnsRecommendation, analyse


def test_unrelated_repo_is_no_action(tmp_path: Path):
    (tmp_path / "x.py").write_text("print('hi')\n", encoding="utf-8")
    a = analyse(tmp_path)
    assert a.recommendation is CnsRecommendation.NO_ACTION
    assert a.cns_modified == "NO"
    # did not write anything extra
    assert list(p.name for p in tmp_path.iterdir()) == ["x.py"]


def test_cns_named_tree_is_never_a_rewrite_target(tmp_path: Path):
    cns = tmp_path / "CNS"
    cns.mkdir()
    (cns / "cns").mkdir()
    (cns / "cns" / "__init__.py").write_text('"""cns contracts."""\n', encoding="utf-8")
    a = analyse(cns)
    assert a.recommendation is CnsRecommendation.NO_ACTION
    assert "does not modify" in a.reason.lower() or "DEFER" in a.reason
    assert a.cns_modified == "NO"


def test_a_retired_repository_is_judged_by_its_evidence_not_its_folder_name(tmp_path: Path):
    """The analyser once answered "no action" for any folder named composition-engine. Now the folder decides nothing."""
    retired = tmp_path / "composition-engine"
    retired.mkdir()
    (retired / "x.py").write_text("from cns.gate import GateOutcome\n", encoding="utf-8")
    a = analyse(retired)
    assert a.recommendation is CnsRecommendation.DEFER   # imports cns, declares no dependency on it
    assert "retired" not in a.reason and a.cns_modified == "NO"


def test_a_tree_that_only_mentions_cns_in_its_readme_needs_no_action_and_lists_the_mention(tmp_path: Path):
    (tmp_path / "README.md").write_text("This project will use cns.gate one day.\n", encoding="utf-8")
    (tmp_path / "x.py").write_text("print('hi')\n", encoding="utf-8")
    a = analyse(tmp_path)
    assert a.recommendation is CnsRecommendation.NO_ACTION
    assert a.native_representation == "domain-owned"
    assert a.provenance is not None and [s.path for s in a.provenance.evidence] == ["README.md"]
