"""Burnish as the Finisher, run through Warden's real loop."""

from pathlib import Path

from warden.authorization import grant
from warden.roles import Facts
from warden.suite import SuiteRun
from warden.tagteam import TagTeam

from burnish.finisher import Burnish
from burnish.readme import finalize_readme

FACTS = Facts(suite=SuiteRun(ran=True, passed=2), remaining=(), cycles=1)


class Idle:
    """A drafter with nothing to propose, so the loop converges at once."""

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
    return grant("william", "transform", str(root.resolve()), "code", "test")


def test_the_finisher_proposes_and_never_writes(tmp_path: Path):
    _tree(tmp_path)
    before = (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8")
    proposal = Burnish().finish(tmp_path, "base", FACTS)
    assert {e.path for e in proposal.edits} == {"pkg/__init__.py", "README.md"}
    assert (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8") == before


def test_through_warden_the_code_is_tidied_and_the_readme_keeps_the_authors_words(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(drafter=Idle(), finisher=Burnish()).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision.startswith("ACCEPT") and result.finished
    assert (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8").endswith("VALUE = 1\n")
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "My hand-written intro." in readme
    assert "## Measured facts (generated)" in readme and "1 passed" in readme


def test_nothing_to_finish_means_no_proposal(tmp_path: Path):
    _tree(tmp_path)
    TagTeam(drafter=Idle(), finisher=Burnish()).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    again = Burnish().finish(tmp_path, "base", FACTS)
    assert again is None or [e.path for e in again.edits] == ["README.md"]


def test_finalizing_twice_changes_nothing(tmp_path: Path):
    _tree(tmp_path)
    from burnish.critic import PoetryCritic
    from burnish.narrative import inspect_tree
    narrative = inspect_tree(tmp_path)
    report = PoetryCritic().critique(tmp_path, narrative, FACTS)
    once = finalize_readme("# demo\n\nIntro.\n", narrative, report, "- commentary")
    assert finalize_readme(once, narrative, report, "- commentary") == once


def test_a_missing_readme_is_compiled(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "README.md").unlink()
    proposal = Burnish().finish(tmp_path, "base", FACTS)
    readme = next(e for e in proposal.edits if e.path == "README.md")
    assert readme.new.startswith("# demo") and "CLAIMS VS REALITY" in readme.new


def test_a_suite_that_the_finishing_change_would_break_is_put_back(tmp_path: Path):
    """The guard is Warden's: a tidy that somehow broke the suite would be reverted."""
    _tree(tmp_path)
    (tmp_path / "tests" / "test_x.py").write_text(
        'import pkg\n\n\ndef test_a():\n    assert "x  " == "x  "   \n', encoding="utf-8")
    result = TagTeam(drafter=Idle(), finisher=Burnish()).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision.startswith("ACCEPT")


def _final(tmp_path: Path, intro: str = "# demo\n\nMy hand-written intro.\n") -> str:
    _tree(tmp_path)
    (tmp_path / "README.md").write_text(intro, encoding="utf-8")
    proposal = Burnish().finish(tmp_path, "base", FACTS)
    return next(e for e in proposal.edits if e.path == "README.md").new


def test_an_existing_readme_is_kept_whole_and_only_one_section_is_added(tmp_path: Path):
    intro = "# demo\n\n## Usage\n\nRun it.\n\n## License\n\nApache-2.0.\n"
    final = _final(tmp_path, intro)
    assert final.startswith(intro)
    headings = [line for line in final.splitlines() if line.startswith("## ")]
    assert headings == ["## Usage", "## License", "## Measured facts (generated)"]


def test_no_template_filler_is_written_into_an_existing_readme(tmp_path: Path):
    final = _final(tmp_path)
    for filler in ("WHAT THIS IS", "WHAT IT OWNS", "See the module docstrings",
                   "Here is what the artifact says it is", "UNKNOWN until a test is executed"):
        assert filler not in final


def test_the_review_section_quotes_the_measured_suite(tmp_path: Path):
    final = _final(tmp_path)
    review = final.split("## Measured facts (generated)", 1)[1]
    assert "2 passed" in review


def test_generated_text_has_no_em_or_en_dash_and_the_authors_text_is_left_alone(tmp_path: Path):
    final = _final(tmp_path, "# demo\n\nThe author \u2014 not Burnish \u2014 wrote this.\n")
    head, review = final.split("## Measured facts (generated)", 1)
    assert "\u2014" in head
    assert "\u2014" not in review and "\u2013" not in review


def test_ghost_findings_are_summarised_not_listed(tmp_path: Path):
    from warden.models import Defect, DefectSeverity
    _tree(tmp_path)
    many = tuple(Defect(ghost_id=f"ghost-{n}", summary=f"repeat number {n}", severity=DefectSeverity.LOW,
                        detector="intra_function_duplicate_block")
                 for n in range(9))
    facts = Facts(suite=FACTS.suite, remaining=many, cycles=1)
    proposal = Burnish().finish(tmp_path, "base", facts)
    final = next(e for e in proposal.edits if e.path == "README.md").new
    assert "still reports 9 finding(s) (intra_function_duplicate_block 9)" in final
    assert "repeat number 3" not in final


def test_the_commentary_says_when_a_check_never_ran(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("V = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# T\n\nA thing.\n", encoding="utf-8")
    facts = Facts(suite=None, remaining=(), cycles=0, unmeasured=("ghost", "suite"))
    edit = Burnish().finish(tmp_path, "b", facts).edits[0]
    assert "Not measured: Ghost Tools was not run; the target's own suite was not run." in edit.new
    assert "—" not in edit.new and "–" not in edit.new
