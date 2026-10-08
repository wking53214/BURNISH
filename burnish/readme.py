"""README compilation.

The README is the book of the source. It is compiled from the narrative
the code already contains, plus the critic's negative findings. It must
never claim more than the source and executed evidence establish.

This module only builds text. Writing it into a repository is a
Transformation, and a Transformation needs a human grant (see Warden).
It counts no tests and invents no passing ones: test results arrive from
Warden as `Facts`, and where nothing is known the section says UNKNOWN.
"""

from __future__ import annotations

import re

from .critic import CriticReport
from .narrative import Narrative

__all__ = ["REQUIRED_HEADINGS", "compile_readme", "finalize_readme"]

REQUIRED_HEADINGS = (
    "WHAT THIS IS",
    "WHY IT EXISTS",
    "WHAT IT OWNS",
    "WHAT IT DOES NOT OWN",
    "ARCHITECTURAL STORY",
    "KEY INTERNAL CONCEPTS",
    "IMPORTANT BOUNDARIES",
    "LIFECYCLE / EXECUTION MODEL",
    "WHAT WORKS",
    "WHAT IS BEAUTIFUL",
    "WHAT IS IMPLEMENTED",
    "WHAT IS PROVEN",
    "WHAT IS NOT PROVEN",
    "WHAT DOES NOT WORK",
    "WHAT IS STILL UGLY",
    "KNOWN DEFECTS",
    "ARCHITECTURAL DEBT",
    "WHAT REMAINS OUTSTANDING",
    "CLAIMS VS REALITY",
)

_NOTHING_RECORDED = "- (none recorded in this inspection)"


def compile_readme(
    narrative: Narrative,
    critic: CriticReport,
    *,
    extra_sections: dict[str, str] | None = None,
    practical: str = "",
) -> str:
    """A README draft: one section per required heading, in order.

    A section the caller supplies in `extra_sections` replaces the default
    for that heading. Everything else is derived from the tree and the critic.
    """
    chosen = {**_default_sections(narrative, critic), **(extra_sections or {})}
    body = "\n\n".join(f"## {heading}\n\n{chosen[heading]}" for heading in REQUIRED_HEADINGS)
    description = narrative.description or "(no pyproject description)"
    return f"# {narrative.name}\n\n> {description}\n\n{body}\n\n{practical}\n"


def _default_sections(narrative: Narrative, critic: CriticReport) -> dict[str, str]:
    """What each heading says when the caller has said nothing about it."""
    ugly = _bullets(critic.what_is_ugly, _NOTHING_RECORDED)
    unfinished = _bullets(critic.what_is_unfinished, "- (none recorded)")
    return {
        "WHAT THIS IS": (f"`{narrative.name}` as declared by its own tree. "
                         f"Version `{narrative.version or 'UNKNOWN'}`."),
        "WHY IT EXISTS": "See the module docstrings. If they do not say, that absence is the answer.",
        "WHAT IT OWNS": "- Whatever its modules declare. Modules that never say so are listed as unfinished.",
        "WHAT IT DOES NOT OWN": "- Whatever this README does not have evidence for. Absence of a denial is not a grant.",
        "ARCHITECTURAL STORY": f"{_module_list(narrative)}\n\nConsole scripts: {_scripts(narrative)}",
        "KEY INTERNAL CONCEPTS": "- See class names in the modules above.",
        "IMPORTANT BOUNDARIES": "- Burnish does not infer a runtime path from a directory name.",
        "LIFECYCLE / EXECUTION MODEL": "- UNKNOWN unless a module docstring states it.",
        "WHAT WORKS": "- UNKNOWN until a test is executed and cited.",
        "WHAT IS BEAUTIFUL": _bullets(critic.what_is_beautiful, _NOTHING_RECORDED),
        "WHAT IS IMPLEMENTED": f"- Python modules in this tree: {len(narrative.modules)}",
        "WHAT IS PROVEN": "- Only what an executed test shows. See CLAIMS VS REALITY for what was measured.",
        "WHAT IS NOT PROVEN": ("- Anything no executed test covers.\n"
                               "- Burnish does not claim this README is complete.\n"
                               f"- Critic verdict: {critic.verdict}"),
        "WHAT DOES NOT WORK": "- UNKNOWN. Failures not executed here are not listed as passing.",
        "WHAT IS STILL UGLY": ugly,
        "KNOWN DEFECTS": ugly,
        "ARCHITECTURAL DEBT": unfinished,
        "WHAT REMAINS OUTSTANDING": unfinished,
        "CLAIMS VS REALITY": _claims_versus_reality(critic),
    }


def _bullets(items: tuple[str, ...], when_empty: str) -> str:
    return "\n".join(f"- {item}" for item in items) or when_empty


def _module_list(narrative: Narrative) -> str:
    lines = (f"- `{m.path}`: {_plain(m.purpose) or '(no module docstring)'}"
             for m in narrative.modules
             if not m.path.startswith("tests/") and "Tests/" not in m.path)
    return "\n".join(lines) or "- (no Python modules)"


def _scripts(narrative: Narrative) -> str:
    return ", ".join(name for name, _ in narrative.scripts) or "none declared"


def _claims_versus_reality(critic: CriticReport) -> str:
    claims = "\n".join(f"- `{c.text}`: {_plain(c.note)} [{c.epistemic.value}]" for c in critic.claims)
    return (f"{claims or '- No numeric claims were extracted.'}\n\n"
            f"Critic: **{_plain(critic.verdict)}**")


def _plain(text: str) -> str:
    """Generated text never carries an em or en dash; the author's own prose is never passed through here."""
    return text.replace(" \u2014 ", ": ").replace("\u2014", "-").replace("\u2013", "-")


_CLAIMS_HEADING = re.compile(r"^##[ \t]+claims[ \t]+vs\.?[ \t]+reality[ \t]*$", re.I | re.M)
_NEXT_HEADING = re.compile(r"^##[ \t]+\S", re.M)


def finalize_readme(existing: str, narrative: Narrative, critic: CriticReport,
                    commentary: str = "", measured: dict[str, str] | None = None) -> str:
    """The final README: the author's prose kept as written, the critic's commentary current.

    With no README, one is compiled from the tree. With one, nothing the author
    wrote is touched or duplicated: the only change is a single CLAIMS VS REALITY
    section (replaced if present, appended if not) holding what was measured, the
    critic's verdict and the critic's commentary. No heading is added just
    because the standard lists it; a section with nothing real to say is not
    written. `measured` supplies the suite line when Warden ran a green suite.
    Running it twice changes nothing.
    """
    if not existing.strip():
        return compile_readme(narrative, critic, extra_sections={
            **(measured or {}), "CLAIMS VS REALITY": _claims_versus_reality(critic) + _tail(commentary)})
    text = existing.rstrip("\n") + "\n"
    suite_line = (measured or {}).get("WHAT WORKS", "")
    body = "\n\n".join(part for part in (suite_line, _claims_versus_reality(critic)) if part)
    section = f"## CLAIMS VS REALITY\n\n{body}{_tail(commentary)}\n"
    start = _CLAIMS_HEADING.search(text)
    if start is None:
        return text + "\n" + section
    following = _NEXT_HEADING.search(text, start.end())
    end = following.start() if following else len(text)
    return text[:start.start()] + section + ("\n" + text[end:] if following else "")


def _tail(commentary: str) -> str:
    return f"\n\n{_plain(commentary.strip())}" if commentary.strip() else ""
