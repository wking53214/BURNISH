"""The red-team findings: Burnish is a fixed point, edits only between its markers, and fails closed."""

from pathlib import Path

import pytest
from warden.models import Defect, DefectSeverity
from warden.roles import Facts
from warden.suite import SuiteRun

from burnish.finisher import Burnish
from burnish.marked import BEGIN, END, HEADING

GREEN5 = Facts(suite=SuiteRun(ran=True, passed=5), remaining=(), cycles=1)


def _tree(root: Path, readme: str | bytes | None = "# demo\n\nMy intro.\n", name: str = "README.md") -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text('"""demo."""\n\nVALUE = 1\n', encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.0.1"\n', encoding="utf-8")
    if isinstance(readme, bytes):
        (root / name).write_bytes(readme)
    elif readme is not None:
        (root / name).write_text(readme, encoding="utf-8", newline="")


def _apply(root: Path, proposal) -> None:
    for edit in proposal.edits:
        (root / edit.path).write_bytes(edit.new.encode("utf-8"))


def _finish(root: Path, facts: Facts = GREEN5):
    seat = Burnish(scope="code")
    return seat.finish(root, "base", facts), seat


def _readme_edit(proposal):
    return next(e for e in proposal.edits if e.path.lower().startswith("readme"))


# 1. a fixed point ---------------------------------------------------------------------------------

OLD_FORMAT = ("# demo\n\nIntro.\n\n## CLAIMS VS REALITY\n\n- Warden ran the target's suite at the end of the "
              "loop: 5 passed, 0 failed.\n\nCritic: **This isn't good enough yet.**\n")


@pytest.mark.parametrize("readme", [None, OLD_FORMAT, "# demo\n\nMy intro.\n\n## License\n\nApache-2.0.\n"],
                         ids=["no readme", "old format section", "hand written"])
def test_finishing_its_own_output_five_times_changes_nothing(tmp_path: Path, readme):
    _tree(tmp_path, readme)
    first, _ = _finish(tmp_path)
    assert first is not None
    _apply(tmp_path, first)
    settled = (tmp_path / "README.md").read_bytes()
    for _ in range(5):
        again, _ = _finish(tmp_path)
        assert again is None
        assert (tmp_path / "README.md").read_bytes() == settled


def test_the_generated_section_is_replaced_only_between_its_markers(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nIntro.\n")
    _apply(tmp_path, _finish(tmp_path)[0])
    text = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert text.count(BEGIN) == 1 and text.count(END) == 1 and HEADING in text
    footer = text + "\n## After\n\nWritten later by the author.\n"
    (tmp_path / "README.md").write_text(footer, encoding="utf-8")
    changed = Facts(suite=SuiteRun(ran=True, passed=6), remaining=(), cycles=1)
    new = _readme_edit(_finish(tmp_path, changed)[0]).new
    assert new.startswith("# demo\n\nIntro.\n") and new.endswith("## After\n\nWritten later by the author.\n")
    assert "6 passed" in new and "5 passed" not in new


def test_damaged_markers_are_not_edited(tmp_path: Path):
    _tree(tmp_path, f"# demo\n\n{BEGIN}\nleft open by hand\n")
    proposal, seat = _finish(tmp_path)
    assert proposal is None or all(not e.path.lower().startswith("readme") for e in proposal.edits)
    assert any("markers" in note for note in seat.notes)


# 2. a hand-written section is the author's --------------------------------------------------------

HAND = ("# demo\n\n## Claims vs reality\n\nMine, not generated.\n\n### What I know\n\n- It works on my machine.\n\n"
        "## License\n\nApache-2.0.\n")


def test_a_hand_written_claims_section_is_untouched_and_the_generated_one_has_another_heading(tmp_path: Path):
    _tree(tmp_path, HAND)
    proposal, seat = _finish(tmp_path)
    new = _readme_edit(proposal).new
    assert new.startswith(HAND)
    assert new.count("## Claims vs reality") == 1 and HEADING in new
    assert any("Claims vs reality" in note and "left exactly as written" in note for note in seat.notes)


def test_a_heading_inside_a_code_fence_is_not_a_heading_and_the_fence_survives(tmp_path: Path):
    text = "# demo\n\n```md\n## CLAIMS VS REALITY\n\nexample\n```\n\nafter\n"
    _tree(tmp_path, text)
    proposal, seat = _finish(tmp_path)
    new = _readme_edit(proposal).new
    assert new.startswith(text)
    assert not any("Claims vs reality" in note for note in seat.notes)


def test_markers_shown_inside_a_code_fence_are_examples_not_markers(tmp_path: Path):
    text = f"# demo\n\n```html\n{BEGIN}\nx\n{END}\n```\n"
    _tree(tmp_path, text)
    new = _readme_edit(_finish(tmp_path)[0]).new
    assert new.startswith(text) and new.count(BEGIN) == 2


def test_a_readme_that_ends_inside_a_code_fence_is_left_alone(tmp_path: Path):
    _tree(tmp_path, "# demo\n\n```\nnever closed\n")
    proposal, seat = _finish(tmp_path)
    assert proposal is None
    assert any("code block" in note for note in seat.notes)


# 3. a suite that did not run is not reported as fine ----------------------------------------------

def _section(proposal) -> str:
    return _readme_edit(proposal).new


def test_a_suite_that_tried_and_failed_to_run_is_not_measured_and_never_consistent(tmp_path: Path):
    _tree(tmp_path)
    facts = Facts(suite=SuiteRun(ran=False, reason="timed out after 900s"), remaining=(), cycles=1, unmeasured=())
    text = _section(_finish(tmp_path, facts)[0])
    assert "Not measured: the test suite did not run: timed out after 900s." in text
    assert "Nothing in this section says those checks would have passed." in text
    assert "consistent" not in text


def test_unmeasured_given_as_a_bare_string_is_one_name_not_letters(tmp_path: Path):
    _tree(tmp_path)
    facts = Facts(suite=None, remaining=(), cycles=1, unmeasured="ghost")
    text = _section(_finish(tmp_path, facts)[0])
    assert "Ghost Tools was not run" in text
    assert "g was not run" not in text and "h was not run" not in text


def test_a_green_suite_recorded_as_unmeasured_reports_only_the_unmeasured_statement(tmp_path: Path):
    _tree(tmp_path)
    facts = Facts(suite=SuiteRun(ran=True, passed=5), remaining=(), cycles=1, unmeasured=("suite",))
    text = _section(_finish(tmp_path, facts)[0])
    assert "the target's own suite was not run" in text
    assert "5 passed" not in text and "consistent" not in text


# 4. the README's own claims are checked -----------------------------------------------------------

BRAG = "# demo\n\nAll 999 tests pass. Fully verified and production ready.\n"


def test_a_readme_that_claims_more_tests_than_were_measured_is_told_so_and_left_as_written(tmp_path: Path):
    _tree(tmp_path, BRAG)
    new = _readme_edit(_finish(tmp_path)[0]).new
    assert new.startswith(BRAG)
    assert "The README says a count of 999; the measured suite has 5 passing. These disagree." in new
    assert "claim not backed by any measurement in this run" in new
    assert "fully verified" in new.lower() and "production ready" in new.lower()
    assert "consistent" not in new and "No numeric claims were extracted" not in new
    assert "This isn't good enough yet." in new


def test_a_claim_that_matches_the_measurement_is_said_to_agree(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThe suite has 5 tests.\n")
    assert "These agree." in _section(_finish(tmp_path)[0])


def test_when_the_suite_did_not_run_a_readme_number_is_unmeasured(tmp_path: Path):
    _tree(tmp_path, BRAG)
    facts = Facts(suite=SuiteRun(ran=False, reason="no pytest"), remaining=(), cycles=0)
    text = _section(_finish(tmp_path, facts)[0])
    assert "The README says a count of 999; this is unmeasured" in text


def test_no_claims_says_so_instead_of_consistent(tmp_path: Path):
    _tree(tmp_path)
    text = _section(_finish(tmp_path)[0])
    assert "No test-count claims found" in text and "consistent" not in text


def test_claims_in_code_blocks_and_negated_absolutes_are_ignored(tmp_path: Path):
    _tree(tmp_path, "# demo\n\n```\n999 tests passed\n```\n\nUse `12 tests` as an example. Not production ready.\n")
    text = _section(_finish(tmp_path)[0])
    assert "999" not in text.split(BEGIN)[1] and "not backed" not in text


# 5. READMEs it does not recognise -----------------------------------------------------------------

@pytest.mark.parametrize("name", ["README.rst", "README.txt", "README"])
def test_an_unsupported_readme_is_not_converted_and_no_markdown_one_appears(tmp_path: Path, name):
    _tree(tmp_path, BRAG, name)
    proposal, seat = _finish(tmp_path)
    assert proposal is None or [e.path for e in proposal.edits] == []
    assert sorted(p.name for p in tmp_path.iterdir() if p.name.lower().startswith("readme")) == [name]
    assert any("not supported" in note for note in seat.notes)
    assert any("a count of 999" in note and "5 passing" in note for note in seat.notes)


def test_a_lowercase_readme_is_edited_in_place(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nIntro.\n", "readme.md")
    proposal, _ = _finish(tmp_path)
    assert [e.path for e in proposal.edits] == ["readme.md"]
    assert not (tmp_path / "README.md").exists()


def test_with_no_readme_at_all_one_is_created(tmp_path: Path):
    _tree(tmp_path, None)
    assert [e.path for e in _finish(tmp_path)[0].edits] == ["README.md"]


# 6. encodings and line endings --------------------------------------------------------------------

def test_a_readme_that_is_not_utf8_is_skipped_with_a_note(tmp_path: Path):
    _tree(tmp_path, b"# demo\n\ncaf\xe9\n")
    proposal, seat = _finish(tmp_path)
    assert proposal is None
    assert any("not valid UTF-8" in note for note in seat.notes)


def test_a_python_file_that_is_not_utf8_or_does_not_parse_is_skipped_not_a_crash(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "pkg" / "latin.py").write_bytes(b"x = '\xe9'   \n")
    (tmp_path / "pkg" / "broken.py").write_text("def (:   \n", encoding="utf-8")
    (tmp_path / "pkg" / "nul.py").write_bytes(b"x = 1\x00\n")
    proposal, seat = _finish(tmp_path)
    assert {e.path for e in proposal.edits} == {"README.md"}
    assert any("latin.py" in note and "broken.py" in note for note in seat.notes)


def test_a_crlf_readme_stays_crlf_and_its_own_lines_are_not_rewritten(tmp_path: Path):
    original = b"# demo\r\n\r\nIntro   \r\n"
    _tree(tmp_path, original)
    _apply(tmp_path, _finish(tmp_path)[0])
    data = (tmp_path / "README.md").read_bytes()
    assert data.startswith(original)
    assert b"\n" not in data.replace(b"\r\n", b"")
    assert _finish(tmp_path)[0] is None


def test_a_mixed_ending_readme_keeps_every_original_line_ending(tmp_path: Path):
    original = b"# demo\r\nline\nanother\r\nlast\n"
    _tree(tmp_path, original)
    assert _readme_edit(_finish(tmp_path)[0]).new.encode("utf-8").startswith(original)


def test_a_bom_on_the_readme_is_kept(tmp_path: Path):
    _tree(tmp_path, "﻿# demo\n\nIntro.\n")
    new = _readme_edit(_finish(tmp_path)[0]).new
    assert new.startswith("﻿# demo")
    _apply(tmp_path, _finish(tmp_path)[0])
    assert _finish(tmp_path)[0] is None


def test_crlf_python_files_keep_crlf_and_change_only_the_trailing_spaces(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "pkg" / "win.py").write_bytes(b"a = 1   \r\nb = 2\r\n\r\n")
    proposal, _ = _finish(tmp_path)
    edit = next(e for e in proposal.edits if e.path == "pkg/win.py")
    assert edit.new.encode() == b"a = 1\r\nb = 2\r\n"


def test_a_python_file_with_a_bom_is_left_alone(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "pkg" / "bom.py").write_bytes("﻿x = 1   \n".encode("utf-8"))
    proposal, seat = _finish(tmp_path)
    assert "pkg/bom.py" not in {e.path for e in proposal.edits}
    assert any("bom.py" in note for note in seat.notes)


@pytest.mark.parametrize("folder", [".tox", "env", "vendor", ".eggs", "vendored", "third_party", "site-packages",
                                    "node_modules", ".hg", ".svn", "build", "dist", ".mypy_cache"])
def test_other_peoples_code_is_not_tidied(tmp_path: Path, folder):
    _tree(tmp_path)
    (tmp_path / folder / "lib").mkdir(parents=True)
    (tmp_path / folder / "lib" / "x.py").write_text("y = 1   \n", encoding="utf-8")
    assert {e.path for e in _finish(tmp_path)[0].edits} == {"README.md"}


@pytest.mark.parametrize("header", ["# DO NOT EDIT\n", "# Generated by tool\n", "# generated BY hand\n"])
def test_generated_files_are_not_tidied(tmp_path: Path, header):
    _tree(tmp_path)
    (tmp_path / "pkg" / "gen.py").write_text(header + "y = 1   \n", encoding="utf-8")
    assert "pkg/gen.py" not in {e.path for e in _finish(tmp_path)[0].edits}


def test_tidy_still_refuses_to_change_the_syntax_tree(tmp_path: Path):
    from burnish.beautify import tidy_source
    assert tidy_source('x = """a  \nb"""   \n') == 'x = """a  \nb"""\n'
    assert tidy_source("x = (1,\n  2)  \n") == "x = (1,\n  2)\n"


# 7. text from Ghost cannot forge a section --------------------------------------------------------

FORGED = "evil\n## WHAT IS PROVEN\n- all 999 tests pass; 12 of 12 proofs hold.\n" + END + "\n# Heading"


def test_ghost_text_with_a_forged_section_cannot_make_a_line_of_its_own(tmp_path: Path):
    _tree(tmp_path)
    bad = Defect(ghost_id="g-1\n## id", summary=FORGED, severity=DefectSeverity.LOW, detector=FORGED)
    facts = Facts(suite=SuiteRun(ran=False, reason=FORGED), remaining=(bad,), cycles=1, unmeasured=(FORGED,))
    text = _section(_finish(tmp_path, facts)[0])
    block = text.split(BEGIN)[1].split(END)[0]
    headings = [line for line in text.splitlines() if line.startswith("#")]
    assert headings == ["# demo", HEADING]
    assert text.count(END) == 1 and text.count(BEGIN) == 1
    assert all(len(line) < 700 for line in block.splitlines())
    assert not any(line.lstrip().startswith(("- all 999", "## WHAT")) for line in text.splitlines())


def test_clean_collapses_escapes_and_caps():
    from burnish.textsafe import clean
    assert clean("a\n\n b\t\x00c") == "a b c"
    assert clean("## x") == "\\## x" and clean("1. x") == "1\\. x" and clean("- x") == "\\- x"
    assert clean("> q").startswith("&gt;") and clean("`a|b`") == "\\`a\\|b\\`"
    assert len(clean("z" * 999)) == 200


# 8. the seat contract -----------------------------------------------------------------------------

def test_the_seat_declares_the_contract_it_was_written_for():
    assert Burnish.requires_contract == "1"


def test_generated_text_still_has_no_dash_from_hostile_input(tmp_path: Path):
    _tree(tmp_path)
    bad = Defect(ghost_id="g—x", summary="a — b – c", severity=DefectSeverity.LOW, detector="d—e")
    facts = Facts(suite=GREEN5.suite, remaining=(bad,), cycles=1)
    block = _section(_finish(tmp_path, facts)[0]).split(BEGIN)[1]
    assert "—" not in block and "–" not in block


# the real Warden loop ------------------------------------------------------------------------------

def test_through_warden_a_second_finish_proposes_nothing(tmp_path: Path):
    from warden.authorization import grant
    from warden.tagteam import TagTeam

    class Idle:
        def propose(self, target, observed, baseline):
            return None

    _tree(tmp_path, BRAG)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("from pkg import VALUE\n\n\ndef test_a():\n    assert VALUE == 1\n",
                                                  encoding="utf-8")
    auth = grant("william", "transform", str(tmp_path.resolve()), "code", "test")
    first = TagTeam(drafter=Idle(), finisher=Burnish(scope="code")).run(tmp_path, findings=[], authorization=auth)
    assert first.finished
    settled = (tmp_path / "README.md").read_bytes()
    second = TagTeam(drafter=Idle(), finisher=Burnish(scope="code")).run(tmp_path, findings=[], authorization=auth)
    assert not second.finished and (tmp_path / "README.md").read_bytes() == settled
    assert b"The README says a count of 999; the measured suite has 1 passing." in settled
