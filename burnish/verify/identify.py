"""Identification and normalization: which pieces of prose claim that a program needs, or runs without, a package.

Reported speech is not a claim either: "the old README said every command imports Warden" tells what was said.

A requirement claim names a package the tree knows (a declared dependency or an imported module) and says one of two
things about it:

  * needs: "every command imports Warden and stops without it", "the tool fails when lxml is not installed",
    "only `finish` needs Warden",
  * runs without: "the tool runs without requests installed", "every other command runs as usual without Warden",
    "it does not import yaml".

Each claim is normalized to a scope, a polarity and a package. The scope is "every" (the whole program, however it is
named), "all-but" (every command but one part), "only" (one part needs it, the rest do not) or "part" (one part, with
nothing said about the rest).

A plain "X needs Y" about the whole program is not read as a claim about installing Y: "it needs Warden, a human grant
and a Drafter" is about what it takes to govern a change. A whole-program need is read only when the sentence says the
package is imported, or that the program stops, fails or exits without it, or that it needs Y installed.

Not claims, and never read as one: history ("before 0.5.0, every command stopped without Warden"), a wish or a rule
("the finisher should stop without Warden"), a quotation ('an old note said "every command needs Warden"') and a denial
of the scope ("not every command needs Warden").

WHAT IT DOES NOT OWN
    Finding evidence. It reads words, not the tree, except for the list of package names it is given.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Mapping, Optional

from .sentences import Piece

__all__ = ["RequirementClaim", "requirement_claims"]


@dataclass(frozen=True)
class RequirementClaim:
    """One claim that the program needs, or runs without, one package, in normal form."""

    words: str       # the README's own words
    line: int
    package: str     # the module name the claim is about, as the code imports it
    needs: bool      # True: the program needs it; False: it runs without it
    scope: str       # "every", "all-but", "only" or "part"
    part: str = ""   # the part named by an "only", "all-but" or "part" scope

    @property
    def normal(self) -> str:
        """The claim in one form, whatever words the README used."""
        who = {"every": "every command", "all-but": f"every command but {self.part}", "only": f"only {self.part}",
               "part": self.part}[self.scope]
        return f"{who} {'needs' if self.needs else 'runs without'} {self.package}"


_TOKEN = re.compile(r"[A-Za-z0-9_]+(?:['’][a-z]+)?(?:[.\-][A-Za-z0-9_]+)*")
_QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”|‘[^’]*’|(?<!\w)'[^']+'(?!\w)")

_IMPORT = frozenset({"imports", "import", "loads"})
_NEED = frozenset({"needs", "need", "requires", "require"})
_STOP = frozenset({"stops", "stop", "fails", "fail", "exits", "exit", "crashes", "crash", "errors", "aborts", "breaks"})
_RUN = frozenset({"runs", "run", "works", "work", "starts", "start"})
_NEGATOR = frozenset({"not", "never", "neither", "nor", "doesn't", "don't", "doesn\u2019t", "don\u2019t", "cannot"})
#: A word before "imports" or "needs" that makes it a noun: "its imports", "the needs of".
_DETERMINER = frozenset({"its", "the", "their", "his", "her", "our", "your", "a", "an", "of", "these", "those", "my"})
#: Words in a subject that carry no part: "Without it, `finish` says Warden is missing and exits" names `finish`.
_FILLER = frozenset({"without", "if", "when", "is", "are", "not", "installed", "missing", "and", "says", "say", "what",
                     "that", "then", "also", "does", "do"})
#: A subject that is only a pronoun points at something said elsewhere; it is never taken to mean the whole program.
_PRONOUN = frozenset({"it", "this", "that", "they", "these", "those"})
#: A part named in more words than this is not a part but a sentence about something else.
_MOST_PART_WORDS = 4
_MISSING = frozenset({"missing", "absent", "uninstalled"})
_INSTALL = frozenset({"installed", "package", "extra"})
_EVERY = frozenset({"every", "all", "each", "any"})
_COMMAND = frozenset({"command", "commands", "subcommand", "subcommands"})
_EXCEPT = frozenset({"but", "except", "other"})
#: Words a whole-program subject is made of: "the tool", "it", "this package", "every command".
_WHOLE = frozenset({"the", "a", "tool", "cli", "program", "package", "library", "app", "application",
                    "everything", "code", "command", "commands", "every", "all", "each", "any", "of", "its", "always"})
_HISTORY = frozenset({"before", "previously", "formerly", "originally", "earlier", "once", "until", "used", "was",
                      "were", "had", "stopped", "needed", "required", "imported", "failed", "crashed", "exited", "ran",
                      "worked", "started"})
_WISH = frozenset({"should", "would", "could", "might", "will", "shall", "may", "must", "plan", "plans", "planned",
                   "goal", "aim", "aims", "eventually", "someday", "ought", "want", "wants", "hope", "intend"})
#: Words that report what someone else said: "the old README said every command needs Warden" is reported speech.
_REPORTED = frozenset({"said", "says", "say", "claimed", "claims", "stated", "states", "wrote", "writes", "reported",
                       "reports", "read", "reads"})
_YEAR = re.compile(r"^(?:19|20)\d\d(?:-\d\d){0,2}$")


@dataclass(frozen=True)
class _Word:
    text: str     # lowercase
    start: int
    quoted: bool


def _words(text: str) -> list[_Word]:
    spans = [m.span() for m in _QUOTED.finditer(text)]
    return [_Word(m.group(0).lower().rstrip("."), m.start(), any(a <= m.start() < b for a, b in spans))
            for m in _TOKEN.finditer(text)]


def _clauses(text: str) -> Iterator[str]:
    """The clauses of a sentence, with asides in parentheses set aside: "(run on a machine with CNS only)" is not the claim."""
    text = re.sub(r"\([^()]*\)", " ", text)
    yield from (part for part in re.split(r"[;:]\s+|\s+\u2014\s+", text) if part.strip())


def requirement_claims(piece: Piece, packages: Mapping[str, str], project: str = "") -> list[RequirementClaim]:
    """The requirement claims `piece` makes. `packages` maps each word that names a package to the module name."""
    out = []
    for clause in _clauses(piece.text):
        claim = _read_clause(clause, piece, packages, project.lower())
        if claim is not None:
            out.append(claim)
    return out


def _read_clause(clause: str, piece: Piece, packages: Mapping[str, str], project: str) -> Optional[RequirementClaim]:
    words = _words(clause)
    plain = [w.text for w in words]
    at = next((i for i, w in enumerate(words) if not w.quoted and w.text in packages), None)
    if at is None:
        return None
    if any(w in _HISTORY or w in _WISH or _YEAR.match(w) for w in plain):
        return None   # history, or a wish, a goal or a rule: not a claim about the program now
    verbs = [i for i, w in enumerate(words) if not w.quoted and w.text in _IMPORT | _NEED | _STOP | _RUN
             and not (i and plain[i - 1] in _DETERMINER)]
    if not verbs:
        return None
    if any(w in _REPORTED for w in plain[:min(verbs)]):
        return None   # reported speech: someone else's claim, told here, not made here
    if any(plain[i] == "not" and i + 1 < len(plain) and plain[i + 1] in _EVERY for i in range(len(plain))):
        return None   # "not every command needs X" denies the scope
    without = _without(plain, at)
    negated = any(plain[j] in _NEGATOR for i in verbs for j in range(max(0, i - 2), i))
    said = {plain[i] for i in verbs}
    only = "only" in plain[:max(verbs)]
    if said & _RUN and without and (_all_but(plain) or not said & _STOP):
        needs = False
    elif said & _STOP and without:
        needs = True
    elif said & _RUN and without:
        needs = False
    elif said & (_IMPORT | _NEED) and negated:
        needs = False
    elif said & _IMPORT or (said & _NEED and (only or _installed(plain, at))):
        needs = True
    else:
        return None
    scope, part = _scope(words, at, verbs, only, project)
    if scope == "part" and len(part.split("(")[0].split()) > _MOST_PART_WORDS:
        return None
    return RequirementClaim(clause.strip()[:120], piece.line, packages[plain[at]], needs, scope, part)


def _all_but(plain: list[str]) -> bool:
    """True for "every other command", "all other commands", "every command but finish"."""
    return any((w in _EVERY and set(plain[i + 1:i + 3]) & _EXCEPT) or
               (w in _COMMAND and plain[i + 1:i + 2] in (["but"], ["except"])) for i, w in enumerate(plain))


def _without(plain: list[str], at: int) -> bool:
    """True when the package sits in a "without X" phrase, or the clause says it is not installed or is missing."""
    if "without" in plain[max(0, at - 3):at]:
        return True
    after = plain[at + 1:at + 4]
    return bool(set(after) & _MISSING) or ("not" in after and "installed" in after)


def _installed(plain: list[str], at: int) -> bool:
    """True for "needs X installed", "requires the X package", "needs the X extra"."""
    return bool(set(plain[max(0, at - 2):at + 3]) & _INSTALL)


def _scope(words: list[_Word], at: int, verbs: list[int], only: bool, project: str) -> tuple[str, str]:
    """The scope the clause gives the claim, and the part it names."""
    plain = [w.text for w in words]
    if only:
        start = plain.index("only") + 1
        stop = next((i for i in verbs if i > start), len(plain))
        return "only", " ".join(p for p in plain[start:stop] if p != plain[at] and p not in ("the", "a"))
    for i, word in enumerate(plain):
        if word in _EVERY and set(plain[i + 1:i + 3]) & _EXCEPT:
            return "all-but", "the part the sentence names"
        if word in _COMMAND and i + 1 < len(plain) and plain[i + 1] in ("but", "except"):
            return "all-but", plain[i + 2] if i + 2 < len(plain) else ""
    first = min(verbs)
    if any(w in _EVERY and set(plain[i + 1:i + 4]) & _COMMAND for i, w in enumerate(plain[:first])):
        return "every", ""   # "every `burnish` command, `--version` included, imports ...": the scope is said outright
    subject =[p for j, p in enumerate(plain[:first]) if j != at and p not in _FILLER and p not in _NEGATOR
               and not (j and plain[j - 1] == "without" and p in _PRONOUN)]
    if subject and all(p in _PRONOUN for p in subject):
        return "part", f"{' '.join(subject)} (what it points at is not resolved)"
    if all(p in _WHOLE or p == project for p in subject):
        return "every", ""
    return "part", " ".join(subject)
