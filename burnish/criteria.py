"""The criteria for beautiful code, as data.

Each criterion has a stable ID, a one-line statement, a level that says who
can judge it, and a source. The prose that explains them lives in
`docs/CRITERIA.md`, `docs/languages/` and `docs/CRAFT.md`; a test fails if
this table and those documents disagree, so neither can drift alone.

LEVELS (who can judge a criterion)

  MECHANICAL  a program can check it from the tree, with no opinion needed
  PROPOSED    a program can suggest a change; a person decides
  HUMAN       only a person who knows the intent can judge it

HOW IMPLEMENTED IT IS

  `state` uses the epistemic vocabulary shared with Warden. IMPLEMENTED means
  Burnish's own checker enforces it today. DESIGNED means it is written
  down and an exemplar follows it, but nothing in Burnish checks it yet.
  NOT_IMPLEMENTED is said out loud rather than left out.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from warden.epistemic import EpistemicState

from .readme_critic import RULES as README_RULES

__all__ = ["Level", "Criterion", "CRITERIA", "by_id", "for_scope"]


class Level(str, Enum):
    """Who can judge a criterion."""

    MECHANICAL = "mechanical"
    PROPOSED = "proposed"
    HUMAN = "human"


@dataclass(frozen=True)
class Criterion:
    """One rule, with a stable ID, who can judge it, and how far it is implemented."""

    id: str
    name: str
    statement: str
    level: Level
    state: EpistemicState
    source: str
    scope: str = "any"  # "any" | "python" | "rust" | "cpp23" | "readme"
    owner: str = "Burnish"  # "Warden" for the rules that govern change itself
    check: Optional[str] = None  # the checks.py check ID that enforces it, if any


_WARDEN_MD = "Elegant.md (Reporting repository)"
_PEP8 = "PEP 8, https://peps.python.org/pep-0008/"
_RUST = "Rust API Guidelines, https://rust-lang.github.io/api-guidelines/checklist.html"
_CORE = "C++ Core Guidelines, https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines"
_CPPREF = "cppreference C++23, https://en.cppreference.com/w/cpp/23"

_I = EpistemicState.IMPLEMENTED
_D = EpistemicState.DESIGNED
_M, _P, _H = Level.MECHANICAL, Level.PROPOSED, Level.HUMAN

CRITERIA: tuple[Criterion, ...] = (
    # -- Principles (Elegant.md section I) --------------------------------------------------
    Criterion("PA", "Naming as truth", "A name must match the contract it represents.", _P, _D, _WARDEN_MD),
    Criterion("PB", "Narrative documentation",
              "Code tells what it does, why it exists, and what it cannot do, before the code itself.",
              _P, _D, _WARDEN_MD),
    Criterion("PC", "Architectural properties as comments",
              "Every non-obvious property (atomicity, fallback, lifecycle, threading) is written inline.",
              _H, _D, _WARDEN_MD),
    # -- Rewriting rules (Elegant.md section II) --------------------------------------------
    Criterion("R1", "Rename without changing behavior",
              "Change the name to match the implementation; fix a wrong implementation in a separate pass.",
              _P, _D, _WARDEN_MD),
    Criterion("R2", "Preserve existing call sites",
              "Callers keep working unmodified. If they cannot, it is a redesign, not a beautification.",
              _H, _D, _WARDEN_MD),
    Criterion("R3", "Add guards without changing logic",
              "A guard wraps existing logic; it never replaces it.", _P, _D, _WARDEN_MD),
    Criterion("R4", "Fix naming references systematically",
              "Rename in one pass: files, includes, namespaces, then verify by building.", _P, _D, _WARDEN_MD),
    Criterion("R5", "Document defects before fixing them",
              "On the first pass, write defects down and make them falsifiable; do not fix yet.",
              _H, _I, _WARDEN_MD, owner="Warden"),
    Criterion("R6", "Validate architectural boundaries",
              "Each layer's contract is enforced by a test, not by a comment.", _H, _D, _WARDEN_MD),
    Criterion("R7", "Behavior-preservation gate",
              "No change merges without a green suite before and after.", _M, _I, _WARDEN_MD, owner="Warden"),
    Criterion("R8", "Scope control",
              "Default scope is the critical path; widen only after a durable audit exists for it.",
              _H, _D, _WARDEN_MD),
    Criterion("R9", "Durable defect IDs",
              "Every defect has a stable ID in one audit file; IDs never change meaning.",
              _M, _I, _WARDEN_MD, owner="Warden"),
    Criterion("R10", "Re-anchor mutation sites, never weaken them",
              "When code moves, move its mutation sites with it; never delete a mutant to let a move pass.",
              _H, _D, _WARDEN_MD),
    Criterion("R11", "Documentation moves with behavior",
              "A commit that changes behavior changes the README in the same pull request.",
              _M, _D, _WARDEN_MD),
    # -- Python (PEP 8) ---------------------------------------------------------------------
    Criterion("PY-EXC", "No bare except", "Name the exceptions you handle; a bare except hides bugs.",
              _M, _I, _PEP8, "python", check="PY-EXC"),
    Criterion("PY-SWALLOW", "No swallowed errors",
              "A handler whose body is only `pass` makes a failure look like success.",
              _M, _I, _PEP8 + " and Elegant.md exemplar (swallowed exceptions)", "python", check="PY-SWALLOW"),
    Criterion("PY-STAR", "No wildcard imports", "Say what you import, so a reader can find where a name came from.",
              _M, _I, _PEP8, "python", check="PY-STAR"),
    Criterion("PY-DOC", "Docstrings on the public surface",
              "Every public module, class and function says what it is for.", _M, _I, _PEP8, "python",
              check="PY-DOC"),
    Criterion("PY-NAME", "Conventional names",
              "Functions are lowercase_with_underscores, classes are CapWords.", _M, _I, _PEP8, "python",
              check="PY-NAME"),
    Criterion("PY-CMP", "Compare to singletons correctly",
              "Use `is` for None and no `== True`; equality is not identity.", _M, _I, _PEP8, "python",
              check="PY-CMP"),
    Criterion("PY-RET", "Consistent returns",
              "Either every path returns a value or none does.", _M, _I, _PEP8, "python", check="PY-RET"),
    Criterion("PY-TYPE", "Annotated signatures", "Public functions declare parameter and return types.",
              _M, _I, _PEP8 + " (PEP 484)", "python", check="PY-TYPE"),
    # -- Rust (API Guidelines) --------------------------------------------------------------
    Criterion("RS-NAME", "Conversions named by cost",
              "as_ is a cheap view, to_ is an expensive copy, into_ consumes.", _P, _D, _RUST, "rust"),
    Criterion("RS-TYPES", "Types instead of ambiguous arguments",
              "Use newtypes and enums, not bare bool or Option, to say what an argument means.",
              _P, _D, _RUST, "rust"),
    Criterion("RS-DOC", "Examples, errors and panics documented",
              "Every public item has a runnable example, and says when it errors or panics. Examples use `?`.",
              _P, _D, _RUST, "rust"),
    Criterion("RS-DEBUG", "Debug on every public type", "A public type can always print itself, never as empty.",
              _M, _D, _RUST, "rust"),
    Criterion("RS-PRIVATE", "Private fields", "Keep struct fields private so the type can change later.",
              _M, _D, _RUST, "rust"),
    Criterion("RS-VALIDATE", "Validate arguments", "Reject bad input at the boundary with a typed error.",
              _H, _D, _RUST, "rust"),
    # -- C++23 (Core Guidelines and cppreference) -------------------------------------------
    Criterion("CX-EXPLICIT", "Say it in code",
              "Express intent in types and names; compilers do not read comments (P.1).", _P, _D, _CORE, "cpp23"),
    Criterion("CX-TYPES", "Strong, explicit interfaces",
              "Interfaces are precisely and strongly typed (I.4) and avoid swappable adjacent parameters (I.24).",
              _P, _D, _CORE, "cpp23"),
    Criterion("CX-PRE", "State preconditions",
              "Say what a function requires of its caller, and check it (I.5, I.6).", _H, _D, _CORE, "cpp23"),
    Criterion("CX-OWN", "No ownership through raw pointers",
              "Ownership moves with an owning type, never a raw pointer or reference (I.11).",
              _M, _D, _CORE, "cpp23"),
    Criterion("CX-GLOBAL", "No mutable globals", "Interfaces depend on what they are given (I.2).",
              _M, _D, _CORE, "cpp23"),
    Criterion("CX-EXPECTED", "Expected failures as values",
              "Use std::expected for failures a caller should handle; reserve exceptions for the rest.",
              _P, _D, _CPPREF, "cpp23"),
    Criterion("CX-NODISCARD", "Results that must be used",
              "Mark a result that a caller must not ignore [[nodiscard]].", _M, _D, _WARDEN_MD, "cpp23"),
    Criterion("CX-SUPPORT", "Know the compiler",
              "std::print, import std and std::mdspan are version-sensitive; the target compiler decides.",
              _H, _D, _CPPREF, "cpp23"),
    # -- Craft: the practices that make code a work of art (docs/CRAFT.md) -------------------
    Criterion("CR1", "Make illegal states impossible",
              "Design types so wrong usage cannot be written.", _H, _D, "docs/CRAFT.md"),
    Criterion("CR2", "Deep, simple interfaces", "A small surface that hides a lot of complexity.", _H, _D,
              "docs/CRAFT.md"),
    Criterion("CR3", "Names are the first documentation", "A precise name removes the need for a comment.",
              _P, _D, "docs/CRAFT.md"),
    Criterion("CR4", "Explain why, not what", "Comments carry intent, constraints and rejected alternatives.",
              _H, _D, "docs/CRAFT.md"),
    Criterion("CR5", "Tests that state rules", "Property tests and mutation tests over example tests.", _H, _D,
              "docs/CRAFT.md"),
    Criterion("CR6", "One way to do each thing", "Each concept lives in exactly one place.", _P, _D,
              "docs/CRAFT.md"),
    Criterion("CR7", "Fail loudly, early, specifically", "Validate at the boundary; never return a quiet empty result.",
              _M, _D, "docs/CRAFT.md"),
    Criterion("CR8", "One level of abstraction per function", "A function reads like an outline.", _P, _D,
              "docs/CRAFT.md"),
    Criterion("CR9", "Consistent shape", "The same problem is solved the same way everywhere.", _H, _D,
              "docs/CRAFT.md"),
    Criterion("CR10", "Delete code", "Dead code, stale flags and unused options are noise.", _P, _D,
              "docs/CRAFT.md"),
    Criterion("CR11", "Decision notes beside the code", "A short 'why we chose this' file next to what it explains.",
              _H, _D, "docs/CRAFT.md"),
)


def _readme_criteria() -> tuple[Criterion, ...]:
    """One criterion per README rule, so the critic's rules and this table cannot drift apart."""
    return tuple(
        Criterion(rule.id, rule.name, f"({rule.tier.value}) {rule.blunt}", Level.MECHANICAL,
                  EpistemicState.IMPLEMENTED, rule.source, "readme", check=rule.id)
        for rule in README_RULES)


CRITERIA = CRITERIA + _readme_criteria()


def by_id(criterion_id: str) -> Criterion:
    """The criterion with this ID; a KeyError names the ID if there is none."""
    for criterion in CRITERIA:
        if criterion.id == criterion_id:
            return criterion
    raise KeyError(f"no criterion {criterion_id!r}")


def for_scope(scope: str) -> tuple[Criterion, ...]:
    """The criteria that apply to one language, plus those that apply to all."""
    return tuple(c for c in CRITERIA if c.scope in ("any", scope))
