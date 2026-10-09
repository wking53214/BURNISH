"""The poetry critic.

Its job is not to praise the code. It is allowed — required — to say:

    This isn't good enough yet.

It does not produce a beauty score. It reads the README and module prose
against what the tree declares, and it speaks about what was measured by
others: the suite result Warden ran and the findings Ghost Tools still
reports, both handed to it as `Facts`. It counts and detects nothing itself.

A README is allowed to contain negative findings. That is a feature.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from warden.epistemic import EpistemicState
from warden.roles import Facts

from .claims import absolutes, judge, test_claims
from .measured import Measured, measure
from .narrative import Narrative, inspect_tree
from .textsafe import clean


@dataclass(frozen=True)
class Claim:
    """One claim a document makes, what kind of evidence backs it, and whether the tree agrees."""

    text: str
    location: str
    epistemic: EpistemicState
    supported: bool
    note: str


@dataclass(frozen=True)
class CriticReport:
    """The critic's whole answer: a verdict, the claims checked, and what is beautiful, ugly and unfinished."""

    target: str
    good_enough: bool
    verdict: str
    claims: tuple[Claim, ...]
    what_is_beautiful: tuple[str, ...]
    what_is_ugly: tuple[str, ...]
    what_is_unfinished: tuple[str, ...]
    unsupported: tuple[str, ...]
    unknown: tuple[str, ...]
    #: How many test-count claims the README prose makes (0 means none were found, which is not the same as "all fine").
    readme_test_claims: int = 0

    def as_markdown(self) -> str:
        """The report as a markdown document."""
        lines = [
            f"# Poetry critic — {self.target}",
            "",
            self.verdict,
            "",
            "## Claims vs reality",
        ]
        for c in self.claims:
            mark = "supported" if c.supported else "UNSUPPORTED"
            lines.append(f"- ({c.epistemic.value}, {mark}) {c.text} — {c.note}")
        lines += ["", "## What is beautiful"]
        lines += [f"- {x}" for x in self.what_is_beautiful] or ["- (nothing recorded)"]
        lines += ["", "## What is still ugly"]
        lines += [f"- {x}" for x in self.what_is_ugly] or ["- (nothing recorded)"]
        lines += ["", "## What is unfinished"]
        lines += [f"- {x}" for x in self.what_is_unfinished] or ["- (nothing recorded)"]
        if self.unsupported:
            lines += ["", "## Unsupported"]
            lines += [f"- {x}" for x in self.unsupported]
        if self.unknown:
            lines += ["", "## UNKNOWN"]
            lines += [f"- {x}" for x in self.unknown]
        return "\n".join(lines) + "\n"


@dataclass
class _Notes:
    """What the critic has noticed so far, in the order it noticed it."""

    claims: list[Claim] = field(default_factory=list)
    ugly: list[str] = field(default_factory=list)
    beautiful: list[str] = field(default_factory=list)
    unfinished: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)


class PoetryCritic:
    """Brutally honest. No scores."""

    def critique(self, root: Path, narrative: Narrative | None = None,
                 facts: Facts | None = None) -> CriticReport:
        """Read the tree's documents against what the tree declares and what was measured."""
        nar = narrative or inspect_tree(Path(root))
        notes = _Notes()
        measured = measure(facts) if facts is not None else None
        _read_readme(nar, notes)
        _speak_about_measurements(measured, notes)
        claimed = _check_readme_claims(nar, measured, notes)
        _check_historical_as_current(nar, notes)
        _check_ownership(nar, notes)
        _check_cns(nar, notes)
        parse_failures = _check_parse_failures(nar, notes)
        notes.unknown.extend(clean(item) for item in nar.unknowns)

        good_enough = not notes.unsupported and not parse_failures
        return CriticReport(
            target=nar.name,
            good_enough=good_enough,
            verdict=_VERDICT_GOOD if good_enough else _VERDICT_NOT_YET,
            claims=tuple(notes.claims),
            what_is_beautiful=tuple(notes.beautiful),
            what_is_ugly=tuple(notes.ugly),
            what_is_unfinished=tuple(notes.unfinished),
            unsupported=tuple(notes.unsupported),
            unknown=tuple(notes.unknown),
            readme_test_claims=claimed,
        )


_VERDICT_NOT_YET = "This isn't good enough yet."
_VERDICT_GOOD = (
    "The artifact's story is consistent with what this inspection could count. "
    "That is not a proof of the whole architecture."
)


def _read_readme(nar: Narrative, notes: _Notes) -> None:
    """A missing README is the first ugliness; a brochure with no admissions is the second."""
    if not nar.readme_exists:
        notes.ugly.append("There is no README. The book of the source is missing.")
        notes.unfinished.append("README")
        return
    honest = _has_honest_sections(nar.readme_text)
    if honest:
        notes.beautiful.append("The README already distinguishes ownership, non-goals, and honest status.")
    if _sounds_like_marketing(nar.readme_text) and not honest:
        notes.ugly.append("The README reads as a product brochure. It does not say what is still ugly.")
        notes.unsupported.append("polished README without a claims-vs-reality section")


def _speak_about_measurements(measured: Measured | None, notes: _Notes) -> None:
    """Quote the suite result and Ghost's remaining findings; say plainly when none were given."""
    if measured is None:
        notes.unknown.append("No measurements were handed to the critic: the suite result and "
                             "Ghost's findings are UNKNOWN here.")
        return
    suite = measured.suite
    if suite is None:
        why = next((s for s in measured.not_run if "suite" in s), "the suite was not run")
        notes.unfinished.append(f"The suite result is unmeasured ({why}), so nothing here is "
                                "backed by an executed test.")
    elif suite.green:
        notes.beautiful.append(f"Warden ran the target's suite at the end of the loop: {suite.describe()}.")
    else:
        notes.ugly.append(f"The target's suite is not green: {suite.describe()}.")
        notes.unsupported.append("a suite that is not green")
    for defect in measured.remaining:
        notes.ugly.append(f"Ghost still reports {clean(defect.identity)}: {clean(defect.summary)}")
    notes.unknown.append(f"The loop ran {measured.cycles} change cycle(s); "
                         "finished means no proposals were left, not that Ghost is silent.")


def _check_readme_claims(nar: Narrative, measured: Measured | None, notes: _Notes) -> int:
    """Check the README's own test counts and absolutes against the measured suite. It only reports; it never rewrites.

    Returns how many test-count claims the prose makes.
    """
    claims = test_claims(nar.readme_text)
    suite = measured.suite if measured is not None else None
    for claim in claims:
        agrees, sentence = judge(claim, suite)
        notes.claims.append(Claim(text=claim.text, location="README",
                                  epistemic=EpistemicState.VERIFIED if suite else EpistemicState.UNKNOWN,
                                  supported=agrees, note=sentence))
        if suite and not agrees:
            notes.unsupported.append(sentence)
        elif not suite:
            notes.unknown.append(sentence)
    for phrase in absolutes(nar.readme_text):
        note = "claim not backed by any measurement in this run"
        notes.claims.append(Claim(text=phrase, location="README", epistemic=EpistemicState.UNKNOWN,
                                  supported=False, note=note))
        notes.unsupported.append(f"'{phrase}': {note}")
    return len(claims)


def _check_historical_as_current(nar: Narrative, notes: _Notes) -> None:
    """A README that teaches installation as if current, in a tree that knows it is retired."""
    living = bool(re.search(r"\bpip install\b", nar.readme_text)) and bool(re.search(r"\bUsage\b", nar.readme_text))
    archived = bool(re.search(r"\b(ARCHIVED|Retired|superseded|historical reconstruction)\b",
                              nar.readme_text, re.I))
    if living and not archived and _github_archive_hint(nar):
        notes.ugly.append("The README teaches installation and usage as if this were the "
                          "current home of the design, without saying it is historical.")
        notes.unsupported.append("living-product README on a superseded artifact")


def _check_ownership(nar: Narrative, notes: _Notes) -> None:
    if nar.owns:
        notes.beautiful.append("At least one module states ownership in its own voice.")
    else:
        notes.unfinished.append("No module states WHAT IT OWNS in the first screen of prose.")


def _check_cns(nar: Narrative, notes: _Notes) -> None:
    """A CNS mention is a fact about the text, not proof of a correct seam."""
    if not nar.cns_mentioned:
        return
    notes.claims.append(Claim(
        text="CNS is referenced",
        location="tree",
        epistemic=EpistemicState.IMPLEMENTED,
        supported=True,
        note="A CNS mention is not proof of a correct seam. Subject binding is UNKNOWN until inspected.",
    ))
    notes.unknown.append("Whether any CNS digest here is the CNS canonical digest.")


def _check_parse_failures(nar: Narrative, notes: _Notes) -> list[str]:
    """A file that cannot be parsed is reported, never skipped; silence would read as clean."""
    failures = [m.path for m in nar.modules if m.purpose == "(unparseable)"]
    for path in failures:
        notes.ugly.append(f"{clean(path)} could not be parsed. Structural detectors cannot speak for it.")
        notes.unfinished.append(clean(path))
    return failures


def _has_honest_sections(text: str) -> bool:
    keys = ("WHAT IT DOES NOT", "What It Does NOT", "Brutally Honest", "CLAIMS VS REALITY", "What is still ugly")
    return sum(1 for k in keys if k in text) >= 2


def _sounds_like_marketing(text: str) -> bool:
    return bool(re.search(r"\b(powerful|seamless|state-of-the-art|simply works)\b", text, re.I)) or (
        "pip install" in text and "does NOT" not in text and "does not" not in text.lower()
    )


def _github_archive_hint(nar: Narrative) -> bool:
    """Local signal that the tree itself already knows it is historical.

    We do not fetch GitHub. PROVENANCE.md or ARCHITECTURE.md mentioning
    retirement / vendoring is enough.
    """
    root = Path(nar.root)
    for name in ("PROVENANCE.md", "ARCHITECTURE.md", "STACK.md"):
        p = root / name
        if p.is_file():
            t = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"retired|vendored|superseded|archived", t, re.I):
                return True
    return False
