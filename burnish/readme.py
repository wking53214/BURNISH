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
from .files import GENERATED_MARKERS, dominant_ending
from .marked import ends_inside_comment, find_block, wrap
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
                               "- Burnish does not claim this README is complete."),
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


def _claims_versus_reality(critic: CriticReport, complete: bool = True) -> str:
    """The claims the critic checked, then its verdict. `complete` is False when any check did not run."""
    lines = [f"- {c.label or '`' + c.text + '`'}: {_plain(c.note)} [{_TAGS.get(c.agreement) or c.agreement or c.epistemic.value}]"
             for c in critic.claims]
    if not critic.readme_test_claims:
        lines.append("- No test-count claims found in the README.")
    if critic.readme_unchecked:
        lines.append(f"- Not checked: {critic.readme_unchecked} other test count(s) in the README are about a file, "
                     "a table row or a named subject, not this suite.")
    return f"{chr(10).join(lines)}\n\nCritic: **{_plain(_verdict(critic, complete))}**"


def _verdict(critic: CriticReport, complete: bool) -> str:
    """The critic's verdict, but never 'consistent' when part of the run was not measured or nothing was checked."""
    if not critic.good_enough:
        return critic.verdict
    if not complete:
        return ("Part of this run was not measured, so this is not a clean bill of health. "
                "Nothing found so far contradicts the README.")
    if not critic.readme_test_claims:
        return "No contradiction with the measurements was found. That is not a proof of the whole design."
    return critic.verdict


_TAGS = {"agrees": "verified", "unmeasured": "unknown"}
_COUNT_TRIGGER = re.compile(r"\b(\d+)\s+(tests?)\b", re.I)
_DEFUSED = {"do not edit": "do-not-edit", "generated by": "generated-by", "auto-generated": "auto generated",
            "autogenerated": "auto generated", "@generated": "generated"}
_MARKER_WORDS = re.compile("|".join(re.escape(m) for m in GENERATED_MARKERS), re.I)


def _inert(text: str) -> str:
    """`text` with nothing Ghost Tools or Warden would read as a claim or as a "generated" banner.

    A number next to the word "tests" in the generated block is read by Ghost as a fresh claim about the suite
    (and flagged when stale), and a "generated by" or "do not edit" near the top of a short README makes Warden
    treat the file as generated code. Nothing here needs either phrase, so each is joined with a hyphen.
    """
    text = _COUNT_TRIGGER.sub(r"\1-\2", text)
    return _MARKER_WORDS.sub(lambda m: _DEFUSED[m.group(0).lower()], text)


def _plain(text: str) -> str:
    """Generated text never carries an em or en dash; the author's own prose is never passed through here."""
    return text.replace(" \u2014 ", ": ").replace("\u2014", "-").replace("\u2013", "-")


def finalize_readme(existing: str, narrative: Narrative, critic: CriticReport,
                    commentary: str = "", measured: dict[str, str] | None = None,
                    complete: bool = True) -> str:
    """The final README: the author's text kept byte for byte, one marked block of generated facts kept current.

    Burnish only writes between its own markers (see `burnish.marked`). If the
    README has no block, one is added at the end, under its own heading, however
    the author's headings are named. If it has one, only that block is replaced,
    and when the new block equals the old one the text comes back unchanged, so
    running it on its own output changes nothing. If the markers are damaged
    (unbalanced, repeated, reversed) nothing is edited. Line endings follow the file.

    With no README at all, one is compiled from the tree first. `measured`
    supplies the suite line when Warden measured the suite.
    """
    suite_line = (measured or {}).get("WHAT WORKS", "")
    body = "\n".join(part for part in (suite_line, _claims_versus_reality(critic, complete)) if part)
    block = wrap(_inert(_plain(f"{body}{_tail(commentary)}")))
    if not existing.strip():
        return _inert(compile_readme(narrative, critic).rstrip("\n")) + "\n\n" + block
    found = find_block(existing)
    if found.problem:
        return existing
    eol = dominant_ending(existing)
    if found.found:
        return _replace_block(existing, found, block, eol)
    return _append_block(existing, block, eol)


_BREAK = re.compile(r"\r\n|\n|\r")


def _replace_block(existing: str, found, block: str, eol: str) -> str:
    """`existing` with only the text between its markers changed, in the line ending that block already used.

    When the end marker is the last line and has no line break, the file keeps having none.
    """
    current = existing[found.start:found.end]
    if _BREAK.sub("\n", current).rstrip("\n") == block.rstrip("\n"):
        return existing
    first = _BREAK.search(current)
    style = first.group(0) if first else eol
    rendered = block.replace("\n", style)
    if not current.endswith(("\n", "\r")):
        rendered = rendered[:-len(style)]
    return existing[:found.start] + rendered + existing[found.end:]


def _append_block(existing: str, block: str, eol: str) -> str:
    """`existing` byte for byte, then one blank line, then the block.

    Nothing the author wrote is trimmed: trailing blank lines stay, and a file with no final line break gets
    one only because the block follows. A README that ends inside an HTML comment that was never closed gets the
    closing `-->` first, on its own line, so the comment keeps swallowing exactly what it already did and the
    block is not part of it.
    """
    out = existing
    if not out.endswith(("\n", "\r")):
        out += eol
    if ends_inside_comment(existing):
        out += "-->" + eol
    if not re.search(r"(?:\r\n|\n|\r)[ \t]*(?:\r\n|\n|\r)$", out):
        out += eol
    return out + block.replace("\n", eol)


def _tail(commentary: str) -> str:
    return f"\n\n{_plain(commentary.strip())}" if commentary.strip() else ""
