"""What Warden measured, checked before anything is said about it.

`Facts` arrives from Warden and is taken as data, not trusted. This module
reads it once and answers three plain questions, the same way for every caller:

  * which checks did not run, whether Warden listed them or Burnish can see it
    for itself (a suite that tried and failed to run is not a measurement),
  * the suite result that may be quoted: only a suite that ran and was not
    recorded as unmeasured, so a result is never reported as both measured and not, and
  * the open Ghost findings.

Every name, id and reason that came from the facts is made safe to print.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from warden.models import Defect
from warden.suite import SuiteRun

from .textsafe import clean

__all__ = ["Measured", "measure"]

_CHECKS = {"ghost": "Ghost Tools was not run", "swizzle": "SWIZZLE's proofs were not run",
           "suite": "the target's own suite was not run"}


@dataclass(frozen=True)
class Measured:
    """The facts, made safe: what may be quoted, and what must be reported as not measured."""

    suite: Optional[SuiteRun]
    remaining: tuple[Defect, ...]
    cycles: int
    not_run: tuple[str, ...]   # plain sentences, one per check that did not run
    names: tuple[str, ...]     # the same checks by name, lower case

    @property
    def complete(self) -> bool:
        """True when every check ran and the suite result can be quoted."""
        return not self.not_run


def _names(raw: Any) -> list[str]:
    """The `unmeasured` field as a list of names: a bare string is one name, never iterated by character."""
    if raw is None:
        return []
    if isinstance(raw, (str, bytes)):
        return [raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw]
    try:
        return [item if isinstance(item, str) else str(item) for item in raw]
    except TypeError:
        return [str(raw)]


def measure(facts: Any) -> Measured:
    """Read `facts` (or None) into what may be said about it."""
    named = [n.strip() for n in _names(getattr(facts, "unmeasured", ())) if n.strip()] if facts is not None else \
        ["ghost", "suite"]
    suite = getattr(facts, "suite", None)
    suite = suite if isinstance(suite, SuiteRun) else None
    sentences: dict[str, str] = {}
    for name in named:
        key = name.lower()
        sentences.setdefault(key, _CHECKS.get(key, f"{clean(name, 60)} was not run"))
    if suite is not None and not suite.ran:
        sentences["suite"] = f"the test suite did not run: {clean(suite.reason, 120) or 'no reason was given'}"
    elif suite is None:
        sentences.setdefault("suite", _CHECKS["suite"])
    if "suite" in sentences:
        suite = suite if suite is not None and suite.ran and "suite" not in {n.lower() for n in named} else None
    remaining = getattr(facts, "remaining", ())
    remaining = tuple(remaining) if isinstance(remaining, (tuple, list)) else ()
    cycles = getattr(facts, "cycles", 0)
    return Measured(suite, remaining, cycles if isinstance(cycles, int) else 0,
                    tuple(sentences.values()), tuple(sentences))
