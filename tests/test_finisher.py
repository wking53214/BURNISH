"""Streamline as the Finisher, run through Elegant's real loop."""

from pathlib import Path

from elegant.authorization import grant
from elegant.roles import Facts
from elegant.suite import SuiteRun
from elegant.tagteam import TagTeam

from streamline.finisher import Streamline
from streamline.readme import finalize_readme

FACTS = Facts(suite=SuiteRun(ran=True, passed=2), remaining=(), cycles=1)


class Idle:
    """A proposer with nothing to propose, so the loop converges at once."""

    def propose(self, target, observed, baseline):
        return None


def _tree(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text('"""demo package."""\n\nVALUE = 1   \n', encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text(
        "from pkg import VALUE\n\n\ndef test_a():\n    assert VALUE == 1\n", encoding="utf-8")
    (root / "README.md").write_text("# demo\n\nMy hand-written intro.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndescription = "demo"\n', encoding="utf-8")


def _auth(root: Path):
    return grant("william", "transform", str(root.resolve()), "finish", "test")


def test_the_finisher_proposes_and_never_writes(tmp_path: Path):
    _tree(tmp_path)
    before = (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8")
    proposal = Streamline().finish(tmp_path, "base", FACTS)
    assert {e.path for e in proposal.edits} == {"pkg/__init__.py", "README.md"}
    assert (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8") == before


def test_through_elegant_the_code_is_tidied_and_the_readme_keeps_the_authors_words(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(proposer=Idle(), finisher=Streamline()).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "ACCEPT" and result.finished
    assert (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8").endswith("VALUE = 1\n")
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "My hand-written intro." in readme
    assert "## CLAIMS VS REALITY" in readme and "1 passed" in readme


def test_nothing_to_finish_means_no_proposal(tmp_path: Path):
    _tree(tmp_path)
    TagTeam(proposer=Idle(), finisher=Streamline()).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    again = Streamline().finish(tmp_path, "base", FACTS)
    assert again is None or [e.path for e in again.edits] == ["README.md"]


def test_finalizing_twice_changes_nothing(tmp_path: Path):
    _tree(tmp_path)
    from streamline.critic import PoetryCritic
    from streamline.narrative import inspect_tree
    narrative = inspect_tree(tmp_path)
    report = PoetryCritic().critique(tmp_path, narrative, FACTS)
    once = finalize_readme("# demo\n\nIntro.\n", narrative, report, "- commentary")
    assert finalize_readme(once, narrative, report, "- commentary") == once


def test_a_missing_readme_is_compiled(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "README.md").unlink()
    proposal = Streamline().finish(tmp_path, "base", FACTS)
    readme = next(e for e in proposal.edits if e.path == "README.md")
    assert readme.new.startswith("# demo") and "CLAIMS VS REALITY" in readme.new


def test_a_suite_that_the_finishing_change_would_break_is_put_back(tmp_path: Path):
    """The guard is Elegant's: a tidy that somehow broke the suite would be reverted."""
    _tree(tmp_path)
    (tmp_path / "tests" / "test_x.py").write_text(
        'import pkg\n\n\ndef test_a():\n    assert "x  " == "x  "   \n', encoding="utf-8")
    result = TagTeam(proposer=Idle(), finisher=Streamline()).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "ACCEPT"
