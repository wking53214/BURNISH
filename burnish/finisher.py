"""Burnish as Warden's Finisher: called once, after the loop has converged.

By now Ghost Tools has reported, the Drafter has fixed what it could, and
Warden has measured the suite. Burnish takes the result and does two
things, as one proposal:

  1. tidies the code (see `burnish.beautify`), behavior-preserving, and
  2. keeps one generated section in the README, between its own markers
     (see `burnish.marked`): what was measured, what was not, where the README's
     own numbers disagree with the measurements, and the critic's remarks.
     A repository with no README gets one compiled from its tree.

Burnish writes nothing. It returns a proposal; Warden applies it under the
same gate as every other change and puts it back if the suite breaks or Ghost
finds anything new. Burnish counts no tests and detects no defects: what it
says about either, it quotes from the `Facts` Warden hands it.

WHAT IT WILL NOT DO TO A README

  * It never edits text outside its markers. A hand-written section, even one
    headed "Claims vs reality", is the author's and stays exactly as written.
  * It edits only the README that is there, in that file's own format, and adds
    its section only to Markdown. A reStructuredText or plain-text README is not
    converted; Burnish says so in its notes and reports what it found there.
  * It never reads its own earlier output, so running it on its own result
    proposes nothing.

`Burnish.notes` holds, after each `finish`, what it left alone and why. The same
notes are in the proposal's `architectural_reason`.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Optional

from warden.models import FileEdit, Transformation, TransformationStatus
from warden.roles import Facts

from .beautify import tidy_edits
from .critic import CriticReport, PoetryCritic
from .files import find_readme, read_strict, readme_is_markdown
from .marked import HEADING, find_block, has_heading, unclosed_fence
from .measured import Measured, measure
from .narrative import Narrative, analysis_text, inspect_tree
from .readme import compile_readme, finalize_readme
from .readme_critic import ReadmeCritic, ReadmeReport
from .textsafe import clean

__all__ = ["Burnish"]

_NO_FACTS = Facts(suite=None, remaining=(), cycles=0, unmeasured=("ghost", "suite"))


class Burnish:
    """The Finisher: `warden tagteam --finisher burnish.finisher:Burnish`."""

    #: The seat contract this Finisher was written against. Warden warns when it is missing and refuses a mismatch.
    requires_contract = "1"

    def __init__(self) -> None:
        self.notes: list[str] = []

    def finish(self, target: Path, baseline: str, facts: Facts) -> Optional[Transformation]:
        """One proposal: tidied code and the README's generated section, or None if neither would change."""
        target = Path(target).resolve()
        self.notes = []
        facts = facts if facts is not None else _NO_FACTS
        edits = tidy_edits(target, self.notes)
        readme = self._readme_edit(target, facts, measure(facts))
        if readme is not None:
            edits.append(readme)
        if not edits:
            return None
        return Transformation(
            target=str(target),
            intent="finish: tidy the code and keep the README's generated facts section current",
            architectural_reason="The loop has converged; this is the single hand-off to Burnish."
                                 + (" Notes: " + " ".join(self.notes) if self.notes else ""),
            affected_files=tuple(e.path for e in edits),
            expected_behavior="Python behavior unchanged (every tidied file parses to the same syntax tree)",
            preservation_requirements=("the target's suite result is unchanged",
                                       "Ghost reports no finding it did not report before"),
            known_defects=tuple(measure(facts).remaining),
            transformation_scope="finish",
            baseline_reference=baseline,
            evidence=tuple(clean(d.identity) for d in measure(facts).remaining),
            edits=tuple(edits),
            status=TransformationStatus.PROPOSED,
        )

    def _readme_edit(self, target: Path, facts: Facts, measured: Measured) -> Optional[FileEdit]:
        """The edit to the README that is there (or a new README.md), or None, with the reason in the notes."""
        path = find_readme(target)
        raw = ""
        if path is not None:
            if path.is_symlink():
                self.notes.append(f"{clean(path.name)} is a link, so it was not edited.")
                return None
            try:
                raw = read_strict(path)
            except (OSError, ValueError):
                self.notes.append(f"{clean(path.name)} is not valid UTF-8 or cannot be read, so it was not edited.")
                return None
        narrative = inspect_tree(target)
        if path is not None and not readme_is_markdown(path):
            self._report_only(path, narrative, facts, measured)
            return None
        if raw.strip():
            problem = self._refuse(raw, path)
            if problem:
                self.notes.append(problem)
                return None
            base = raw
            if has_heading(raw, r"claims\s+vs\.?\s+reality") and not find_block(raw).found:
                self.notes.append(f"{path.name} has its own Claims vs reality section; it was left exactly as written. "
                                  f"The generated facts are in a separate section headed \"{HEADING[3:]}\".")
        else:
            base = self._compiled(target, narrative, facts, measured)
            narrative = dataclasses.replace(narrative, readme_exists=True, readme_text=analysis_text(base))
        name = path.name if path is not None else "README.md"
        report = PoetryCritic().critique(target, narrative, facts)
        gaps = ReadmeCritic().critique_text(target, name, analysis_text(base))
        new = finalize_readme(base, narrative, report, _commentary(report, gaps, measured), _suite_line(measured),
                              complete=measured.complete)
        return None if new == raw else FileEdit(path=name, kind="write", new=new, old=raw)

    def _refuse(self, raw: str, path: Optional[Path]) -> str:
        """Why the README cannot be edited safely, or an empty string when it can."""
        block = find_block(raw)
        if block.problem:
            return f"{clean(path.name)}: {block.problem}, so the README was not edited."
        if not block.found and unclosed_fence(raw):
            return f"{clean(path.name)} ends inside a code block, so nothing was added to it."
        return ""

    def _compiled(self, target: Path, narrative: Narrative, facts: Facts, measured: Measured) -> str:
        """A README compiled from the tree, for a repository that has none. It is written once and then belongs to the author."""
        report = PoetryCritic().critique(target, narrative, None)  # nothing measured is frozen into the body
        report = dataclasses.replace(
            report, what_is_ugly=tuple(x for x in report.what_is_ugly if "no readme" not in x.lower()),
            what_is_unfinished=tuple(x for x in report.what_is_unfinished if x != "README"))
        pointer = f"- See the \"{HEADING[3:]}\" section at the end of this file. It is rewritten on each finish."
        return compile_readme(narrative, report, extra_sections={
            "WHAT WORKS": pointer, "WHAT IS PROVEN": pointer, "CLAIMS VS REALITY": pointer,
            "KNOWN DEFECTS": pointer}).rstrip("\n") + "\n"

    def _report_only(self, path: Path, narrative: Narrative, facts: Facts, measured: Measured) -> None:
        """A README format Burnish cannot add a section to: leave it, and put what it found in the notes."""
        self.notes.append(f"The README is {clean(path.name)}; that format is not supported for the generated "
                          "section, so none was added and the file was not converted.")
        report = PoetryCritic().critique(path.parent, narrative, facts)
        self.notes += [f"Not measured: {item}." for item in measured.not_run]
        self.notes += [f"README says: {clean(c.text, 80)}: {clean(c.note)}"
                       for c in report.claims if c.location == "README" and not c.supported]


def _commentary(report: CriticReport, readme: ReadmeReport, measured: Measured) -> str:
    """The critic's words for the README: what did not run, Ghost's open findings in brief, what is unsupported or unknown, then the README critic's gaps."""
    lines = _not_measured(measured) + _ghost_summary(measured)
    lines += [f"- Unsupported: {clean(item, 300)}" for item in report.unsupported]
    lines += [f"- Unknown: {clean(item, 300)}" for item in report.unknown]
    lines += ["" if lines else "", "README critic, on the README as it stood going into the finish:", ""]
    lines += [f"- {clean(gap.render(), 400)}" for gap in (*readme.failures, *readme.gaps)] or ["- no failures or gaps"]
    return "\n".join(lines)


def _not_measured(measured: Measured) -> list[str]:
    """Say so when a check never ran, so an empty list is not read as a clean one."""
    if not measured.not_run:
        return []
    return [f"- Not measured: {'; '.join(measured.not_run)}. Nothing in this section says those checks "
            "would have passed."]


def _ghost_summary(measured: Measured) -> list[str]:
    """One line for what Ghost still reports, by kind. The findings themselves stay in Ghost's report."""
    kinds: dict[str, int] = {}
    for defect in measured.remaining:
        name = clean(defect.detector or "unclassified", 60)
        kinds[name] = kinds.get(name, 0) + 1
    if not kinds:
        return []
    ordered = sorted(kinds.items(), key=lambda item: (-item[1], item[0]))
    by_kind = ", ".join(f"{name} {count}" for name, count in ordered)
    return [f"- Ghost Tools still reports {len(measured.remaining)} finding(s) ({by_kind}). "
            "Converged means no fixes were left to propose, not that Ghost is silent."]


def _suite_line(measured: Measured) -> dict[str, str]:
    """Section text that quotes the suite result Warden measured, only when the suite ran and is not recorded as unmeasured."""
    suite = measured.suite
    if suite is None:
        return {}
    return {"WHAT WORKS": f"- Warden ran the target's suite at the end of the loop: {clean(suite.describe(), 300)}."}
