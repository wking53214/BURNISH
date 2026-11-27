"""Campaign 2: claims verification in stages, six verdict states, and evidence provenance on every verdict."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from burnish.critic import PoetryCritic
from burnish.narrative import inspect_tree
from burnish.provenance import Provenance, Source
from burnish.verify.evidence import read_tree
from burnish.verify.identify import requirement_claims
from burnish.verify.sentences import Piece, pieces
from burnish.verify.verdict import FINAL, State, Verdict, verdict_of_row

ROOT = Path(__file__).resolve().parent.parent

#: The sentence Burnish's README carried in 0.5.11, false since 0.5.0, which the critic passed.
OLD_SENTENCE = ("Standalone here means outside the circuit, not without Warden: every `burnish` command, `burnish --version` "
                "included, imports the Warden package and stops with `No module named 'warden'` when Warden is not "
                "installed (run on a machine holding Burnish and CNS only).")

PACKAGES = {"warden": "warden", "cns": "cns", "lxml": "lxml"}


def _provenance(evidence: tuple[Source, ...] = (Source("pyproject.toml", 3, "x"),), basis: str = "direct") -> Provenance:
    return Provenance(claim="c", claim_at=Source("README", 1), evidence=evidence, method="m", basis=basis,  # type: ignore[arg-type]
                      not_inspected=(), reason="r")


def _read(text: str) -> list[str]:
    return [c.normal for piece in pieces(text) for c in requirement_claims(piece, PACKAGES, "demo")]


# ---------------------------------------------------------------- the verdict states

def test_there_are_exactly_the_six_states_the_mission_names():
    assert {s.value for s in State} == {"CLAIM_IDENTIFIED", "EVIDENCE_FOUND", "EVIDENCE_SUPPORTS", "EVIDENCE_CONTRADICTS",
                                        "EVIDENCE_INSUFFICIENT", "NOT_CHECKED"}


def test_absence_of_evidence_is_never_falsity():
    with pytest.raises(ValueError, match="needs evidence"):
        Verdict(State.EVIDENCE_CONTRADICTS, _provenance(evidence=()))
    with pytest.raises(ValueError, match="never falsity"):
        Verdict(State.EVIDENCE_CONTRADICTS, _provenance(basis="none"))


def test_a_step_on_the_way_is_not_a_verdict():
    with pytest.raises(ValueError):
        Verdict(State.EVIDENCE_FOUND, _provenance())


def test_the_trail_shows_whether_evidence_was_found():
    assert Verdict(State.EVIDENCE_SUPPORTS, _provenance()).trail == (
        State.CLAIM_IDENTIFIED, State.EVIDENCE_FOUND, State.EVIDENCE_SUPPORTS)
    assert Verdict(State.EVIDENCE_INSUFFICIENT, _provenance(evidence=(), basis="none")).trail == (
        State.CLAIM_IDENTIFIED, State.EVIDENCE_INSUFFICIENT)


@pytest.mark.parametrize("supported, agreement, state", [
    (True, "agrees", State.EVIDENCE_SUPPORTS), (True, "holds for an optional dependency only", State.EVIDENCE_SUPPORTS),
    (False, "disagrees", State.EVIDENCE_CONTRADICTS), (False, "unmeasured", State.EVIDENCE_INSUFFICIENT),
    (False, "unverifiable", State.EVIDENCE_INSUFFICIENT), (False, "unconfirmed", State.EVIDENCE_INSUFFICIENT),
    (False, "unchecked", State.EVIDENCE_INSUFFICIENT), (False, "", State.EVIDENCE_INSUFFICIENT)])
def test_every_kind_of_row_maps_to_one_state(supported, agreement, state):
    evidence = (Source("x", 1),) if state is not State.EVIDENCE_INSUFFICIENT else ()
    verdict = verdict_of_row(supported, agreement, _provenance(evidence=evidence, basis="direct" if evidence else "none"))
    assert verdict is not None and verdict.state is state


def test_every_row_of_the_report_on_burnish_has_a_final_verdict():
    report = PoetryCritic().critique(ROOT)
    assert report.claims
    assert all(row.verdict is not None and row.verdict.state in FINAL for row in report.claims + report.not_checked)
    assert "Verdict: EVIDENCE_SUPPORTS (CLAIM_IDENTIFIED > EVIDENCE_FOUND > EVIDENCE_SUPPORTS)" in report.as_markdown()


# ---------------------------------------------------------------- the false negative Campaign 2 started from

def test_the_old_warden_sentence_is_now_contradicted_by_burnish_s_own_tree():
    narrative = replace(inspect_tree(ROOT), readme_text=f"# burnish\n\n{OLD_SENTENCE}\n")
    report = PoetryCritic().critique(ROOT, narrative)
    rows = [row for row in report.claims if row.kind == "requires"]
    assert [row.verdict.state for row in rows if row.verdict] == [State.EVIDENCE_CONTRADICTS]
    assert report.outcome.value == "FAIL"
    provenance = rows[0].provenance
    assert provenance is not None and provenance.basis == "inferred"
    shown = "; ".join(source.render() for source in provenance.evidence)
    assert "entry point burnish = burnish.cli:run" in shown
    assert "declares warden only as an optional dependency" in shown
    assert "burnish/finisher.py" in shown and "behind a guard" in shown


def test_burnish_s_own_readme_makes_no_requirement_claim_its_tree_contradicts():
    report = PoetryCritic().critique(ROOT)
    assert report.outcome.value == "PASS"
    assert [r for r in report.claims if r.kind == "requires" and not r.supported] == []


# ---------------------------------------------------------------- identification: what is and is not a claim

@pytest.mark.parametrize("text, normal", [
    (OLD_SENTENCE.replace("burnish", "demo"), "every command needs warden"),
    ("The tool runs without lxml installed.", "every command runs without lxml"),
    ("Every command fails when lxml is missing.", "every command needs lxml"),
    ("The tool does not import lxml.", "every command runs without lxml"),
    ("Only `demo finish` needs Warden.", "only demo finish needs warden"),
    ("Without Warden, `demo finish` exits 2 and every other command runs as usual.", "every command but the part the "
     "sentence names runs without warden"),
    ("## Every command runs without lxml installed", "every command runs without lxml"),
    ("| Requirement | Every command runs without lxml installed |", "every command runs without lxml"),
    ("> The tool runs without lxml installed.", "every command runs without lxml"),
])
def test_a_requirement_claim_is_read_in_one_normal_form(text, normal):
    assert _read(text) == [normal]


@pytest.mark.parametrize("text", [
    "Before 0.5.0, every command stopped when Warden was not installed.",       # history
    "On 2026-11-18 every command stops without Warden.",                         # dated history
    "If Warden is missing, the finisher should say so and stop.",                # a rule
    "One day the tool will run without lxml installed.",                         # a wish
    'An old note said "every command needs Warden".',                            # a quotation
    "The old README said every command imports Warden and stops without it.",   # reported speech
    "Not every command needs Warden installed.",                                 # a denial of the scope
    "It needs Warden, a human grant and a Drafter.",                             # a need that is not about installing
    "A recommendation decided from its imports and Warden's.",                   # "imports" as a noun
    "```\nevery command imports Warden\n```",                                    # code
])
def test_what_is_not_a_requirement_claim(text):
    assert _read(text) == []


def test_a_pronoun_subject_is_never_the_whole_program():
    assert _read("Now only `demo finish` loads it; without Warden it stops and exits 2.") == [
        "it (what it points at is not resolved) needs warden"]


def test_a_part_with_nothing_said_about_the_rest_is_not_checked_and_changes_no_outcome(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "1"\ndependencies = ["lxml"]\n'
                                             '[project.scripts]\ndemo = "demo.cli:run"\n', encoding="utf-8")
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "__init__.py").write_text('"""Demo."""\n', encoding="utf-8")
    (tmp_path / "demo" / "cli.py").write_text('"""Cli."""\n\nimport lxml\n\n\ndef run():\n    return lxml\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n\nThe parser module imports lxml.\n", encoding="utf-8")
    report = PoetryCritic().critique(tmp_path)
    assert [r.verdict.state for r in report.not_checked if r.verdict] == [State.NOT_CHECKED]
    assert [r for r in report.claims if r.kind == "requires"] == []
    assert "## Identified, not checked" in report.as_markdown()


# ---------------------------------------------------------------- extraction and evidence

def test_extraction_keeps_lines_and_structure():
    got = list(pieces("# Title\n\nFirst one. Second\none.\n\n| a | b |\n|---|---|\n| c | d |\n\n> quoted\n"))
    assert Piece("Title", 1, heading=True) in got
    assert Piece("First one.", 3) in got and Piece("Second one.", 3) in got
    assert Piece("c", 8, table=True) in got and Piece("quoted", 10, blockquote=True) in got


def test_the_reading_of_burnish_finds_warden_only_behind_a_guard():
    reading = read_tree(ROOT, "burnish")
    assert reading.complete()
    assert {route.kind for route in reading.routes["warden"]} == {"guarded"}
    assert "load" in {route.kind for route in reading.routes["cns"]}
    assert "burnish" not in reading.names


def test_every_burnish_subpackage_is_installed():
    """A normal install ships only the packages pyproject.toml lists; `burnish.verify` must be one of them."""
    import tomllib

    listed = set(tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"]["packages"])
    found = {".".join(p.parent.relative_to(ROOT).parts) for p in (ROOT / "burnish").rglob("__init__.py")}
    assert found <= listed, sorted(found - listed)
