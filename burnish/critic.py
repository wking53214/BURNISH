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
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Optional

from cns.epistemic import EpistemicState
from cns.seat import Facts

from .claims import absolutes_at, judge, test_claims, unchecked_mentions
from .drift import Drift, check_test_claims, check_tree_claims, claims_held_by_extras
from .files import find_readme, pyproject_problem_at
from .marked import line_number, source_line_map
from .measured import Measured, describe_suite, measure
from .narrative import Narrative, inspect_tree
from .provenance import Provenance, Source
from .textsafe import clean

#: Kinds of row that are findings about the tree rather than claims a document makes. They are reported with their
#: provenance like every other row, and the generated README section and the finisher's notes leave them out, as before.
TREE_FINDINGS = frozenset({"metadata", "parse", "suite", "readme-shape", "history"})


@dataclass(frozen=True)
class Claim:
    """One claim a document makes, what kind of evidence backs it, and whether the tree agrees."""

    text: str
    location: str
    epistemic: EpistemicState
    supported: bool
    note: str
    #: "agrees", "disagrees" or "unmeasured" for a README number; empty for any other kind of claim.
    agreement: str = ""
    #: A description to print in place of `text` when `text` would repeat the README's own claim.
    label: str = ""
    #: What was checked: "tests", "pin", "dependencies", "absolute" or "cns" for a claim a document makes, or one of
    #: `TREE_FINDINGS` for a finding about the tree. Empty for a row made outside the critic.
    kind: str = ""
    #: Where the verdict comes from, so a reviewer can repeat it (see `burnish.provenance`). Every row the critic makes has one.
    provenance: Optional[Provenance] = None


class Outcome(str, Enum):
    """The critic's top-level answer.

    FAIL: the evidence contradicts a claim, or the tree breaks a rule (a file that does not parse, a suite that is not
    green). INCOMPLETE: nothing is contradicted, but evidence a claim needs could not be had in this run (an unmeasured
    test count, a broken pyproject.toml, an import whose use was not checked). PASS: neither.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


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
    #: How many test counts the README mentions that are about something else (a file, a table row, a named subject).
    readme_unchecked: int = 0
    #: PASS, FAIL or INCOMPLETE. `good_enough` is True only for PASS.
    outcome: Outcome = Outcome.PASS

    def as_markdown(self) -> str:
        """The report as a markdown document."""
        lines = [
            f"# Claims critic: {self.target}",
            "",
            f"Outcome: {self.outcome.value}",
            "",
            self.verdict,
            "",
            "## Claims vs reality",
        ]
        for c in self.claims:
            mark = "supported" if c.supported else "UNSUPPORTED"
            if c.provenance is None:
                lines.append(f"- ({c.epistemic.value}, {mark}) {c.text} — {c.note}")
            else:   # the note is the provenance's reason, printed once with the rest of it
                lines.append(f"- ({c.epistemic.value}, {mark}) {c.text}")
                lines += c.provenance.lines()
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
    #: The unsupported items that are contradictions or broken rules, not missing evidence. Each is also in `unsupported`.
    failing: list[str] = field(default_factory=list)

    def fail(self, item: str) -> None:
        """Record something the evidence contradicts, or a rule the tree breaks: it makes the outcome FAIL."""
        self.unsupported.append(item)
        self.failing.append(item)


class PoetryCritic:
    """Brutally honest. No scores."""

    def critique(self, root: Path, narrative: Narrative | None = None,
                 facts: Facts | None = None, collected: int | None = None) -> CriticReport:
        """Read the tree's documents against what the tree declares and what was measured.

        `collected` is a test count somebody else produced (for example from `pytest --collect-only`). With
        neither it nor `facts`, a number the README gives for its tests is reported as unverifiable.
        """
        nar = narrative or inspect_tree(Path(root))
        notes = _Notes()
        readme = _Readme(nar)
        measured = measure(facts) if facts is not None else None
        _read_readme(nar, readme, notes)
        _speak_about_measurements(facts, measured, notes)
        claimed = _check_readme_claims(nar, readme, facts, measured, notes)
        _check_against_the_tree(nar, readme, facts, collected, notes)
        unchecked = unchecked_mentions(nar.readme_text)
        _check_historical_as_current(nar, readme, notes)
        _check_ownership(nar, notes)
        _check_cns(nar, readme, notes)
        parse_failures = _check_parse_failures(nar, notes)
        notes.unknown.extend(clean(item) for item in nar.unknowns)
        if nar.metadata_problem:
            _check_metadata(nar, notes)

        outcome = (Outcome.FAIL if notes.failing or parse_failures else
                   Outcome.INCOMPLETE if notes.unsupported else Outcome.PASS)
        return CriticReport(
            target=nar.name,
            good_enough=outcome is Outcome.PASS,
            verdict=_VERDICTS[outcome],
            outcome=outcome,
            claims=tuple(notes.claims),
            what_is_beautiful=tuple(notes.beautiful),
            what_is_ugly=tuple(notes.ugly),
            what_is_unfinished=tuple(notes.unfinished),
            unsupported=tuple(notes.unsupported),
            unknown=tuple(notes.unknown),
            readme_test_claims=claimed,
            readme_unchecked=unchecked,
        )


_VERDICTS = {
    Outcome.FAIL: "This isn't good enough yet.",
    Outcome.INCOMPLETE: ("Not finished: some claims could not be checked in this run, and nothing found contradicts them. "
                         "This is not a pass."),
    Outcome.PASS: ("The artifact's story is consistent with what this inspection could count. "
                   "That is not a proof of the whole architecture."),
}


class _Readme:
    """The README file a finding points at, and the way from a line of the text the critic reads to a line of the file.

    The critic reads the README with line ends made LF and Burnish's own block removed; a reviewer opens the file. Each
    line number a check finds is mapped back to the file's own numbering, so it can be opened and read where it says.
    """

    def __init__(self, nar: Narrative) -> None:
        path = find_readme(Path(nar.root)) if nar.readme_exists else None
        self.name = path.name if path is not None else "README"
        self.origin: list[int] = []
        if path is not None:
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                raw = ""
            self.origin = source_line_map(raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n"))

    def at(self, line: int, what: str = "") -> Source:
        """The README at `line` of the text the critic read (0: the whole file)."""
        if 0 < line <= len(self.origin):
            line = self.origin[line - 1]
        return Source(self.name, line, what)

    def line_of(self, nar: Narrative, match: Optional[re.Match[str]]) -> int:
        """The line of the critic's README text that `match` (found in it) starts on, or 0."""
        return line_number(nar.readme_text, match.start()) if match else 0


def _row(notes: _Notes, kind: str, text: str, location: str, epistemic: EpistemicState, supported: bool, agreement: str,
         provenance: Provenance) -> None:
    """Record one row of the report: a finding with its provenance, whose reason is also the row's note."""
    notes.claims.append(Claim(text=text, location=location, epistemic=epistemic, supported=supported,
                              note=provenance.reason, agreement=agreement, kind=kind, provenance=provenance))


_MARKETING = re.compile(r"\b(powerful|seamless|state-of-the-art|simply works)\b", re.I)
_HONEST_KEYS = ("WHAT IT DOES NOT", "What It Does NOT", "Brutally Honest", "CLAIMS VS REALITY", "What is still ugly")


def _read_readme(nar: Narrative, readme: _Readme, notes: _Notes) -> None:
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
        notes.fail("polished README without a claims-vs-reality section")
        word = _MARKETING.search(nar.readme_text) or re.search(r"pip install", nar.readme_text)
        found = (f"the brochure word \"{clean(word.group(0), 40)}\"" if word and _MARKETING.match(word.group(0))
                 else "a pip install line, and no \"does not\" anywhere")
        _row(notes, "readme-shape", "the README says what is still unfinished", "README", EpistemicState.ASSUMED, False,
             "disagrees", Provenance(
                 claim="the README says what is still unfinished (a claims-vs-reality or what-it-does-not section)",
                 claim_at=readme.at(0), evidence=(readme.at(readme.line_of(nar, word), found),),
                 method=("Looked for brochure words (powerful, seamless, state-of-the-art, simply works), or a pip install "
                         "line with no \"does not\" anywhere, and for at least two of the honest-section headings ("
                         + ", ".join(_HONEST_KEYS) + ")."),
                 basis="inferred",
                 not_inspected=("whether the README admits its gaps in other words: only these fixed phrases and headings "
                                "were looked for",),
                 reason=("The README reads as a product brochure and has fewer than two honest-section headings: a polished "
                         "README without a claims-vs-reality section fails the critic.")))


def _speak_about_measurements(facts: Facts | None, measured: Measured | None, notes: _Notes) -> None:
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
        notes.beautiful.append(f"Warden ran the target's suite at the end of the loop: {describe_suite(suite)}.")
    else:
        said = f"The target's suite did not pass at the end of the loop: {describe_suite(suite)}."
        notes.ugly.append(said)
        notes.fail("a suite that is not green")
        _row(notes, "suite", "the target's suite passes", "suite", EpistemicState.ASSUMED, False, "disagrees", Provenance(
            claim="the target's suite passes", claim_at=Source(what="a rule of the critic: the suite must be green"),
            evidence=(_SUITE_SOURCE,),
            method="Read the suite result Warden handed in: green means it ran with no failures and no errors.",
            basis="direct", not_inspected=_SUITE_NOT_INSPECTED, reason=said + " A suite that is not green fails the critic."))
    for defect in measured.remaining:
        notes.ugly.append(f"Ghost still reports {clean(defect.identity)}: {clean(defect.summary)}")
    notes.unknown.append("Finished means the loop had no proposals left, not that Ghost is silent.")


_SUITE_SOURCE = Source(what="the suite result Warden handed in (its passed, failed, errored, skipped and expected-failure "
                             "totals; not a file)")
_SUITE_NOT_INSPECTED = ("which tests ran or failed: Warden hands in totals, not names",
                        "the tests themselves: Burnish runs and counts none")
_JUDGE_METHOD = ("Compared the README's claim with the suite result Warden measured: a bare count must equal the tests that "
                 "passed or every test run; a count said to pass must equal the tests that passed, or every test run when "
                 "the only others were skipped (unless the README says none were); an 'at least' figure must not exceed "
                 "the tests that passed; 'all pass' needs a run with no failures and no errors.")


def _check_readme_claims(nar: Narrative, readme: _Readme, facts: Facts | None, measured: Measured | None,
                         notes: _Notes) -> int:
    """Check the README's own test counts and absolutes against the measured suite. It only reports; it never rewrites.

    Returns how many test-count claims the prose makes.
    """
    claims = test_claims(nar.readme_text)
    suite = measured.suite if measured is not None else None
    for claim in claims:
        agrees, sentence = judge(claim, suite)
        states = ((EpistemicState.VERIFIED, "agrees") if agrees else
                  (EpistemicState.ASSUMED, "disagrees")) if suite else (EpistemicState.UNKNOWN, "unmeasured")
        what = ("all tests pass" if claim.kind == "green" else
                f"count {claim.number}" + (", says passing" if claim.kind == "passing" else ""))
        if suite is not None:
            provenance = Provenance(claim=f'"{claim.text}"', claim_at=readme.at(claim.line), evidence=(_SUITE_SOURCE,),
                                    method=_JUDGE_METHOD, basis="direct", not_inspected=_SUITE_NOT_INSPECTED,
                                    reason=sentence)
        else:
            looked = ("no measurements were handed to the critic" if facts is None else
                      "the measurements handed in hold no suite result, or the suite did not run")
            provenance = Provenance(claim=f'"{claim.text}"', claim_at=readme.at(claim.line), evidence=(),
                                    method=f"Looked for the suite result Warden hands in: {looked}.", basis="none",
                                    not_inspected=("the suite itself: Burnish counts and runs no tests",), reason=sentence)
        notes.claims.append(Claim(text=claim.text, location="README", epistemic=states[0], supported=agrees,
                                  note=sentence, agreement=states[1], label=f"README claim ({what})", kind="tests",
                                  provenance=provenance))
        if suite and not agrees:
            notes.fail(sentence)
        elif not suite:
            notes.unknown.append(sentence)
    for phrase, line in absolutes_at(nar.readme_text):
        note = "claim not backed by any measurement in this run"
        notes.claims.append(Claim(text=phrase, location="README", epistemic=EpistemicState.UNKNOWN, supported=False,
                                  note=note, kind="absolute", provenance=Provenance(
                                      claim=f'"{phrase}"', claim_at=readme.at(line), evidence=(),
                                      method=("Matched the README prose against a fixed list of absolute phrases (fully "
                                              "verified, production ready, battle tested, 100% coverage, no known bugs), "
                                              "leaving out denials, goals and figures scoped to a part."),
                                      basis="none",
                                      not_inspected=("anything that could back an absolute: no coverage report, bug tracker "
                                                     "or release record is read",),
                                      reason=note)))
        notes.unsupported.append(f"'{phrase}': {note}")
    return len(claims)


def _located(drift: Drift, readme: _Readme) -> Provenance:
    """The drift's provenance with its README line made a line of the README file."""
    assert drift.provenance is not None, f"a {drift.kind} drift without provenance"
    return replace(drift.provenance, claim_at=readme.at(drift.line))


def _check_against_the_tree(nar: Narrative, readme: _Readme, facts: Facts | None, collected: int | None,
                            notes: _Notes) -> None:
    """A pin, a dependency list or a test count the README states and the tree contradicts or cannot back."""
    drifts: list[Drift] = check_tree_claims(Path(nar.root), nar.readme_text)
    if facts is None:   # with facts, Warden's measured suite judges the counts instead
        drifts += check_test_claims(nar.readme_text, collected)
    for drift in drifts:
        if drift.verdict != "unverifiable":
            state = EpistemicState.UNKNOWN if drift.verdict in ("unchecked", "unconfirmed") else EpistemicState.ASSUMED
            notes.claims.append(Claim(text=drift.claim, location="README", epistemic=state, supported=False,
                                      note=drift.problem, agreement=drift.verdict, label=f"README claim ({drift.kind})",
                                      kind=drift.kind, provenance=_located(drift, readme)))
        else:   # the count already has its "unmeasured" row from the claim reader: it gets this, fuller, provenance
            _reprove(notes, drift, readme)
        if drift.verdict == "disagrees":
            notes.fail(drift.problem)
        else:   # unverifiable, unchecked or unconfirmed: the evidence was not there, nothing contradicts the claim
            notes.unsupported.append(drift.problem)
    for held in claims_held_by_extras(Path(nar.root), nar.readme_text):
        notes.claims.append(Claim(text=held.claim, location="README", epistemic=EpistemicState.VERIFIED, supported=True,
                                  note=held.problem, agreement="holds for an optional dependency only",
                                  label=f"README claim ({held.kind})", kind=held.kind, provenance=_located(held, readme)))


def _reprove(notes: _Notes, drift: Drift, readme: _Readme) -> None:
    """Give the claim reader's row for an unverifiable count the drift's provenance, which knows about --collected."""
    provenance = _located(drift, readme)
    for index, row in enumerate(notes.claims):
        if row.kind == "tests" and row.agreement == "unmeasured" and row.provenance is not None \
                and row.provenance.claim_at == provenance.claim_at and row.text == drift.claim:
            notes.claims[index] = replace(row, provenance=replace(provenance, reason=f"{row.note} {drift.problem}"))
            return


def _check_historical_as_current(nar: Narrative, readme: _Readme, notes: _Notes) -> None:
    """A README that teaches installation as if current, in a tree that knows it is retired."""
    install = re.search(r"\bpip install\b", nar.readme_text)
    living = bool(install) and bool(re.search(r"\bUsage\b", nar.readme_text))
    archived = bool(re.search(r"\b(ARCHIVED|Retired|superseded|historical reconstruction)\b",
                              nar.readme_text, re.I))
    hint = _github_archive_hint(nar) if living and not archived else None
    if hint is not None:
        said = ("The README teaches installation and usage as if this were the "
                "current home of the design, without saying it is historical.")
        notes.ugly.append(said)
        notes.fail("living-product README on a superseded artifact")
        _row(notes, "history", "the README is the current home of the design", "README", EpistemicState.ASSUMED, False,
             "disagrees", Provenance(
                 claim="the README is the current home of the design (it teaches pip install and Usage)",
                 claim_at=readme.at(readme.line_of(nar, install)),
                 evidence=(readme.at(readme.line_of(nar, install), "a pip install line, with a Usage section"), hint),
                 method=("Looked in the README for a pip install line and the word Usage with no word saying it is "
                         "archived, retired, superseded or a historical reconstruction, and in PROVENANCE.md, "
                         "ARCHITECTURE.md and STACK.md for a word saying the tree is retired, vendored, superseded or "
                         "archived."),
                 basis="inferred",
                 not_inspected=("whether GitHub marks the repository archived: nothing is fetched",
                                "what the matched word refers to: a mention of retiring something else counts too"),
                 reason=said + " A living-product README on a superseded tree fails the critic."))


def _check_ownership(nar: Narrative, notes: _Notes) -> None:
    if nar.owns:
        notes.beautiful.append("At least one module states ownership in its own voice.")
    else:
        notes.unfinished.append("No module states WHAT IT OWNS in the first screen of prose.")


_CNS_MENTION = re.compile(r"\b(?:from cns|import cns|cns\.gate|cns\.graph)\b")


def _check_cns(nar: Narrative, readme: _Readme, notes: _Notes) -> None:
    """A CNS mention is a fact about the text, not proof of a correct seam."""
    if not nar.cns_mentioned:
        return
    note = "A CNS mention is not proof of a correct seam. Subject binding is UNKNOWN until inspected."
    evidence = [Source(clean(m.path), m.cns_line, "mentions CNS") for m in nar.modules if m.cns_import][:5]
    in_readme = _CNS_MENTION.search(nar.readme_text)
    if in_readme:
        evidence.append(readme.at(readme.line_of(nar, in_readme), "mentions CNS"))
    shown = sum(1 for m in nar.modules if m.cns_import)
    notes.claims.append(Claim(
        text="CNS is referenced",
        location="tree",
        epistemic=EpistemicState.IMPLEMENTED,
        supported=True,
        note=note,
        kind="cns",
        provenance=Provenance(
            claim="CNS is referenced", claim_at=Source(what="read from the tree, not a sentence of the README"),
            evidence=tuple(evidence),
            method="Searched the Python files and the README for from cns, import cns, cns.gate or cns.graph.",
            basis="direct",
            not_inspected=("whether the code uses CNS correctly: the seam, subject binding and digest were not inspected",)
            + ((f"{shown - 5} more file(s) that mention CNS, not listed",) if shown > 5 else ()),
            reason=note),
    ))
    notes.unknown.append("Whether any CNS digest here is the CNS canonical digest.")


def _check_metadata(nar: Narrative, notes: _Notes) -> None:
    """A pyproject.toml that is there and cannot be read: listed as UNKNOWN, and as a row a reviewer can open.

    It makes the outcome INCOMPLETE even when the README makes no pin or dependency claim: the tree's own metadata was not
    read, so this run cannot say the tree is consistent. Nothing is contradicted, so it is not a FAIL.
    """
    said = (f"{nar.metadata_problem}: the name, version and description were read line by line and may be wrong or "
            "incomplete, and no pin or dependency was checked.")
    notes.unknown.append(said)
    notes.unsupported.append(f"{nar.metadata_problem}, so the tree's metadata could not be checked; fix it and run the "
                             "critic again.")
    _, line = pyproject_problem_at(Path(nar.root))
    _row(notes, "metadata", "pyproject.toml can be read", "pyproject.toml", EpistemicState.UNKNOWN, False, "unchecked",
         Provenance(claim="pyproject.toml can be read as TOML", claim_at=Source("pyproject.toml"),
                    evidence=(Source("pyproject.toml", line, str(nar.metadata_problem)),),
                    method="Parsed pyproject.toml with Python's tomllib (after reading it as UTF-8).", basis="direct",
                    not_inspected=("every pin and dependency pyproject.toml declares",
                                   "the name, version and description as TOML would give them: they were read line by "
                                   "line instead"),
                    reason=said + " With metadata that could not be read, the critic ends INCOMPLETE, never PASS."))


def _check_parse_failures(nar: Narrative, notes: _Notes) -> list[str]:
    """A file that cannot be parsed is reported, never skipped; silence would read as clean."""
    broken = [m for m in nar.modules if m.purpose == "(unparseable)"]
    for module in broken:
        path = clean(module.path)
        said = f"{path} could not be parsed. Structural detectors cannot speak for it."
        notes.ugly.append(said)
        notes.unfinished.append(path)
        _row(notes, "parse", f"{path} can be parsed", path, EpistemicState.ASSUMED, False, "disagrees", Provenance(
            claim=f"{path} is Python the detectors can read", claim_at=Source(path),
            evidence=(Source(path, module.parse_error_line, clean(module.parse_error or "the parser refused it")),),
            method="Parsed the file with Python's own parser (ast.parse), reading it as UTF-8.", basis="direct",
            not_inspected=("everything in this file: no detector, import scan or ownership check could read it",),
            reason=said + " A file that does not parse fails the critic."))
    return [m.path for m in broken]


def _has_honest_sections(text: str) -> bool:
    return sum(1 for k in _HONEST_KEYS if k in text) >= 2


def _sounds_like_marketing(text: str) -> bool:
    return bool(_MARKETING.search(text)) or (
        "pip install" in text and "does NOT" not in text and "does not" not in text.lower()
    )


def _github_archive_hint(nar: Narrative) -> Optional[Source]:
    """Local signal that the tree itself already knows it is historical: where it is, or None.

    We do not fetch GitHub. PROVENANCE.md or ARCHITECTURE.md mentioning
    retirement / vendoring is enough.
    """
    root = Path(nar.root)
    for name in ("PROVENANCE.md", "ARCHITECTURE.md", "STACK.md"):
        p = root / name
        if p.is_file():
            t = p.read_text(encoding="utf-8", errors="replace")
            word = re.search(r"retired|vendored|superseded|archived", t, re.I)
            if word:
                return Source(name, line_number(t, word.start()), f'says "{word.group(0)}"')
    return None
