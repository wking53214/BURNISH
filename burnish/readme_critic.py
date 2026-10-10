"""The README critic: blunt about gaps and failures, and never scores.

Three tiers, from the research in `docs/README_STANDARD.md`:

  MINIMUM     what a reader needs to decide, install and use the project
              (Standard Readme, GitHub's README guidance, Art of README,
              Make a README). A failure here means the README does not do its job.
  STRONG      what separates a competent README from a forgettable one.
  OVER THE TOP  what the best READMEs add: a picture of the thing, a way in
              within one screen, evidence the claims are true, and an
              honest account of what it will not do. This tier is a synthesis
              of what the awesome-readme examples share; it is a standard Burnish
              sets for itself, not a rule any source states.

The critic reads one README file and the files it links to. It does not run
anything, does not fetch URLs, and says so when a rule needs a check it
cannot make. It is allowed, and required, to say that a README is not good.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator, Optional

__all__ = ["Tier", "Rule", "RULES", "Gap", "ReadmeReport", "ReadmeCritic", "parse"]

_MAX_BYTES = 500 * 1024
_ONE_LINER_LIMIT = 120
_TOC_THRESHOLD = 100
_MAX_BADGES = 8


class Tier(str, Enum):
    """How much a README rule matters: the minimum, strong, or over the top."""

    MINIMUM = "minimum"
    STRONG = "strong"
    OVER_THE_TOP = "over-the-top"


@dataclass(frozen=True)
class Section:
    """One heading and the text under it, up to the next heading."""

    level: int
    title: str
    body: str
    fences: tuple[tuple[str, str], ...]  # (info string, content) of each code fence in the body


@dataclass(frozen=True)
class Readme:
    """A README read once: its text, its headings, and the places it points to."""

    path: Path
    text: str
    lines: tuple[str, ...]
    sections: tuple[Section, ...]
    links: tuple[tuple[str, str], ...]  # (text, target) of every markdown link, images included
    images: tuple[str, ...]

    def section(self, pattern: str) -> Optional[Section]:
        """The first section whose title matches `pattern`, ignoring case."""
        expression = re.compile(pattern, re.I)
        return next((s for s in self.sections if expression.search(s.title)), None)


@dataclass(frozen=True)
class Rule:
    """One README rule, where it comes from, and what the critic says when it fails."""

    id: str
    tier: Tier
    name: str
    source: str
    blunt: str  # what the critic says when the rule fails
    test: Callable[[Readme], Optional[str]]  # None if it holds, else the specific failure


@dataclass(frozen=True)
class Gap:
    """A rule that failed, with the specific reason."""

    rule: Rule
    detail: str

    def render(self) -> str:
        return f"[{self.rule.id}] {self.rule.blunt} ({self.detail})"


@dataclass(frozen=True)
class ReadmeReport:
    """The critic's whole answer about one README, sorted by how much each failure matters."""

    path: str
    failures: tuple[Gap, ...]
    gaps: tuple[Gap, ...]
    reach: tuple[Gap, ...]
    held: tuple[str, ...]
    verdict: str

    @property
    def meets_minimum(self) -> bool:
        return not self.failures

    @property
    def over_the_top(self) -> bool:
        return not (self.failures or self.gaps or self.reach)

    def as_markdown(self) -> str:
        """The report in the critic's own blunt voice."""
        out = [f"# README critic: {self.path}", "", self.verdict, ""]
        for title, items in (("Failures (minimum not met)", self.failures),
                             ("Gaps (not strong)", self.gaps),
                             ("Not over the top", self.reach)):
            if items:
                out += [f"## {title}", *[f"- {gap.render()}" for gap in items], ""]
        if self.held:
            out += ["## What holds", *[f"- {name}" for name in self.held], ""]
        return "\n".join(out)


_BEGIN = "<!-- burnish:begin claims-vs-reality -->"
_END = "<!-- burnish:end -->"


def _without_generated_block(text: str) -> str:
    """The text with Burnish's own generated block removed, so a README is judged without its last finish.

    This is a small copy of `burnish.marked.without_block` on purpose: the README critic
    stands alone and imports nothing else from Burnish. Markers inside a code fence are not markers.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    fenced, commented, begin, end = False, False, [], []
    for number, line in enumerate(lines):
        if commented:
            commented = "-->" not in line or line.strip() in {_BEGIN, _END}
        elif re.match(r"^ {0,3}(`{3,}|~{3,})", line):
            fenced = not fenced
        elif fenced or re.match(r"^(?: {4,}|\t)", line):
            continue  # fenced or indented code: an example, not a marker
        elif line.strip() == _BEGIN:
            begin.append(number)
        elif line.strip() == _END:
            end.append(number)
        elif line.lstrip().startswith("<!--") and "-->" not in line:
            commented = True
    if len(begin) != 1 or len(end) != 1 or end[0] < begin[0]:
        return text
    before = "\n".join(lines[:begin[0]]).rstrip()
    after = "\n".join(lines[end[0] + 1:]).lstrip("\n")
    return (before + ("\n\n" + after if after.strip() else "\n")) if before else after


def parse(path: Path) -> Readme:
    """Read a README into sections, links and images. Fenced code is never mistaken for prose."""
    return parse_text(path, Path(path).read_text(encoding="utf-8", errors="replace"))


def parse_text(path: Path, text: str) -> Readme:
    """Read README text that is already in hand, as if it had been read from `path`."""
    text = _without_generated_block(text.lstrip("\ufeff"))
    lines = tuple(text.splitlines())
    sections = tuple(_sections(lines))
    links = tuple((m.group(1), m.group(2).split()[0]) for m in re.finditer(r"!?\[([^\]]*)\]\(([^)\s]+[^)]*)\)", text))
    images = tuple(m.group(1) for m in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)", text))
    return Readme(Path(path), text, lines, sections, links, images)


def _sections(lines: tuple[str, ...]) -> Iterator[Section]:
    heading: Optional[tuple[int, str]] = None
    body: list[str] = []
    fences: list[tuple[str, str]] = []
    fence_info: Optional[str] = None
    fence_body: list[str] = []
    for line in lines:
        marker = re.match(r"^\s*(```+|~~~+)\s*([^\s`]*)", line)
        if marker:
            if fence_info is None:
                fence_info, fence_body = marker.group(2), []
            else:
                fences.append((fence_info, "\n".join(fence_body)))
                fence_info = None
            body.append(line)
            continue
        if fence_info is not None:
            fence_body.append(line)
            body.append(line)
            continue
        found = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if found:
            if heading is not None:
                yield Section(heading[0], heading[1], "\n".join(body), tuple(fences))
            heading, body, fences = (len(found.group(1)), found.group(2)), [], []
        else:
            body.append(line)
    if heading is not None:
        yield Section(heading[0], heading[1], "\n".join(body), tuple(fences))


# -- the rules ----------------------------------------------------------------------------------

_STANDARD = "Standard Readme spec"
_GITHUB = "GitHub, About READMEs"
_ART = "Art of README"
_MAKE = "Make a README"
_AWESOME = "awesome-readme examples"
_SYNTHESIS = "Burnish synthesis of " + _AWESOME


def _title(r: Readme) -> Optional[str]:
    first = next((line for line in r.lines if line.strip()), "")
    if not re.match(r"^#\s+\S", first):
        return "the first line is not a level-one title"
    return None


def _one_liner(r: Readme) -> Optional[str]:
    after_title = _after_title(r)
    if after_title is None:
        return "there is no sentence under the title"
    if len(after_title) > _ONE_LINER_LIMIT:
        return f"the first sentence is {len(after_title)} characters; the limit is {_ONE_LINER_LIMIT}"
    if after_title.startswith(">"):
        return "the description is a quote block; the spec asks for a plain line"
    return None


def _after_title(r: Readme) -> Optional[str]:
    """The first plain-text line after the title, skipping badges, banners and blank lines."""
    seen_title = False
    for line in r.lines:
        stripped = line.strip()
        if not seen_title:
            seen_title = stripped.startswith("# ")
            continue
        if not stripped or stripped.startswith(("[![", "![", "<", "---")):
            continue
        return None if stripped.startswith("#") else stripped
    return None


def _needs_section(pattern: str, what: str, needs_code: bool = False) -> Callable[[Readme], Optional[str]]:
    def test(r: Readme) -> Optional[str]:
        section = r.section(pattern)
        if section is None:
            return f"no section matching /{pattern}/"
        if needs_code and not section.fences:
            return f"the {what} section has no code block"
        return None
    return test


def _license_named(r: Readme) -> Optional[str]:
    section = r.section(r"licen[cs]e")
    if section is None:
        return "no License section"
    if not re.search(r"apache|mit|bsd|gpl|mpl|isc|unlicense|unlicensed|proprietary|spdx", section.body, re.I):
        return "the License section does not name a license"
    return None


def _links_resolve(r: Readme) -> Optional[str]:
    base = r.path.parent
    broken = []
    for _, target in r.links:
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        path = target.split("#", 1)[0]
        if path and not (base / path).exists():
            broken.append(path)
    return f"links to files that do not exist: {', '.join(sorted(set(broken)))}" if broken else None


def _size(r: Readme) -> Optional[str]:
    size = len(r.text.encode("utf-8"))
    return f"{size} bytes; GitHub truncates past {_MAX_BYTES}" if size > _MAX_BYTES else None


def _toc(r: Readme) -> Optional[str]:
    if len(r.lines) <= _TOC_THRESHOLD:
        return None
    if r.section(r"contents|table of contents") or _quick_links(r) is None:
        return None
    return f"{len(r.lines)} lines and no table of contents"


def _fence_languages(r: Readme) -> Optional[str]:
    bare = sum(1 for section in r.sections for info, _ in section.fences if not info)
    return f"{bare} code block(s) with no language, so no highlighting" if bare else None


def _honest_limits(r: Readme) -> Optional[str]:
    pattern = r"not own|does not|doesn.t|limitation|known (defects|issues)|not proven|claims vs reality|non-goals|what it is not"
    return None if r.section(pattern) else "nowhere does it say what the project will not do"


def _status(r: Readme) -> Optional[str]:
    if r.section(r"status|maintenance|stability") or re.search(r"\bstatus\b\s*[:*]", r.text, re.I):
        return None
    if re.search(r"\b(alpha|beta|stable|experimental|production)\b", "\n".join(r.lines[:40]), re.I):
        return None
    return "no statement of whether this is maintained, experimental or stable"


def _support(r: Readme) -> Optional[str]:
    return None if r.section(r"support|help|questions|contact|issues") else "no place to ask for help"


def _contributing(r: Readme) -> Optional[str]:
    section = r.section(r"contribut")
    if section is None:
        return "no Contributing section"
    return None if re.search(r"pull request|\bPRs?\b|issue|question", section.body, re.I) else (
        "it does not say whether pull requests are accepted or where to ask questions")


def _quick_links(r: Readme) -> Optional[str]:
    head = "\n".join(r.lines[:30])
    inline = re.findall(r"\[[^\]]+\]\((?:#|docs/|[A-Za-z0-9_./-]+\.md)[^)]*\)", head)
    return None if len(inline) >= 3 else "fewer than three navigation links in the first screen"


def _visual(r: Readme) -> Optional[str]:
    has_image = bool(r.images)
    has_diagram = any(info in {"mermaid", "text", "ascii", ""} and re.search(r"[│┌└─▼→]|-->|\+--", body)
                      for section in r.sections for info, body in section.fences)
    return None if has_image or has_diagram else "no image and no diagram: the reader must imagine the thing"


def _demo(r: Readme) -> Optional[str]:
    usage = r.section(r"usage|quick ?start|example|getting started")
    if usage is None:
        return "no usage section to hold a demo"
    shows_output = len(usage.fences) >= 2 or bool(re.search(r"output|prints|returns|\$ |>>> ", usage.body, re.I))
    return None if shows_output or r.images else "usage shows commands but never what comes back"


def _badges(r: Readme) -> Optional[str]:
    count = len(re.findall(r"!\[[^\]]*\]\(https?://[^)]*(shields\.io|badge|actions/workflows)[^)]*\)", "\n".join(r.lines[:20])))
    if count == 0:
        return "no badge in the first screen (CI status, license or version tells a reader something real)"
    return f"{count} badges; past {_MAX_BADGES} they are decoration" if count > _MAX_BADGES else None


def _architecture(r: Readme) -> Optional[str]:
    section = r.section(r"architect|how it works|design")
    if section is None:
        return "no architecture or how-it-works section"
    if not section.fences and not re.search(r"invariant|boundar|decision", section.body, re.I):
        return "the architecture section has no diagram and names no invariants or decisions"
    return None


def _evidence(r: Readme) -> Optional[str]:
    pattern = r"\b\d+ tests?\b|verified by|proven by|ci\b|continuous integration|workflow"
    return None if re.search(pattern, r.text, re.I) else "it claims things without saying how they were checked"


def _faq(r: Readme) -> Optional[str]:
    return None if r.section(r"faq|frequently asked|questions") else "no FAQ"


def _alternatives(r: Readme) -> Optional[str]:
    return None if r.section(r"alternative|compar(e|ison)|why not|versus") else "no comparison with alternatives"


def _roadmap(r: Readme) -> Optional[str]:
    return None if r.section(r"roadmap|outstanding|planned|next") else "no roadmap, so the reader cannot tell where it is going"


def _examples(r: Readme) -> Optional[str]:
    if r.section(r"examples?\b"):
        return None
    return None if any(re.match(r"^(examples?|exemplars?)/", t) for _, t in r.links) else "no runnable examples are linked"


def _decisions(r: Readme) -> Optional[str]:
    linked = any(re.search(r"(decision|adr|design|criteria|rationale)", t, re.I) for _, t in r.links)
    return None if linked or r.section(r"decision|rationale") else "no link to why the design is the way it is"


RULES: tuple[Rule, ...] = (
    Rule("RM-TITLE", Tier.MINIMUM, "Title", _STANDARD, "It does not open with a title.", _title),
    Rule("RM-ONELINER", Tier.MINIMUM, "One-line description", _STANDARD + "; " + _ART,
         "It never says what the project is in one plain sentence.", _one_liner),
    Rule("RM-INSTALL", Tier.MINIMUM, "Install, with a command", _STANDARD + "; " + _MAKE,
         "A reader cannot get this running.", _needs_section(r"install|setup|getting started", "install", True)),
    Rule("RM-USAGE", Tier.MINIMUM, "Usage, with a code block", _STANDARD + "; " + _ART,
         "A reader cannot tell how to use it.", _needs_section(r"usage|quick ?start|example|getting started", "usage", True)),
    Rule("RM-LICENSE", Tier.MINIMUM, "License, named", _STANDARD + "; " + _MAKE,
         "A reader cannot tell whether they may use it.", _license_named),
    Rule("RM-LINKS", Tier.MINIMUM, "No broken relative links", _STANDARD + "; " + _GITHUB,
         "It points at files that are not there.", _links_resolve),
    Rule("RM-SIZE", Tier.MINIMUM, "Under GitHub's size limit", _GITHUB, "GitHub will cut it off.", _size),
    Rule("RM-CONTRIB", Tier.MINIMUM, "Contributing, with a stance", _STANDARD + "; " + _MAKE,
         "Nobody can tell if help is wanted.", _contributing),
    Rule("RM-LIMITS", Tier.MINIMUM, "Says what it will not do", _ART + " (be objective)",
         "It reads as a brochure: no limits are admitted.", _honest_limits),
    Rule("RM-STATUS", Tier.STRONG, "Project status", _MAKE, "A reader cannot tell whether this is alive.", _status),
    Rule("RM-SUPPORT", Tier.STRONG, "Where to get help", _MAKE, "A stuck reader has nowhere to go.", _support),
    Rule("RM-TOC", Tier.STRONG, "Navigation for a long README", _STANDARD + "; " + _GITHUB,
         "It is long and offers no way through.", _toc),
    Rule("RM-FENCES", Tier.STRONG, "Code blocks name their language", _STANDARD,
         "Code is shown unhighlighted.", _fence_languages),
    Rule("RM-EXAMPLES", Tier.STRONG, "Runnable examples", _ART, "No example a reader can run.", _examples),
    Rule("OT-QUICKLINKS", Tier.OVER_THE_TOP, "A way in within one screen", _AWESOME,
         "There is no way to jump to what you came for.", _quick_links),
    Rule("OT-VISUAL", Tier.OVER_THE_TOP, "A picture of the thing", _AWESOME + "; " + _MAKE,
         "There is nothing to look at.", _visual),
    Rule("OT-DEMO", Tier.OVER_THE_TOP, "A demo with its output", _AWESOME + "; " + _MAKE,
         "It never shows the result.", _demo),
    Rule("OT-BADGES", Tier.OVER_THE_TOP, "Badges that carry information", _MAKE + "; " + _ART,
         "No badge tells the reader anything.", _badges),
    Rule("OT-ARCH", Tier.OVER_THE_TOP, "Architecture with invariants", _AWESOME,
         "A contributor cannot see how it fits together.", _architecture),
    Rule("OT-EVIDENCE", Tier.OVER_THE_TOP, "Claims come with their evidence", _SYNTHESIS,
         "It asks to be believed.", _evidence),
    Rule("OT-FAQ", Tier.OVER_THE_TOP, "A FAQ", _AWESOME, "The obvious questions go unanswered.", _faq),
    Rule("OT-ALTERNATIVES", Tier.OVER_THE_TOP, "Compared with the alternatives", _MAKE + "; " + _ART,
         "It does not say why this and not something else.", _alternatives),
    Rule("OT-ROADMAP", Tier.OVER_THE_TOP, "A roadmap", _MAKE, "It does not say where it is going.", _roadmap),
    Rule("OT-DECISIONS", Tier.OVER_THE_TOP, "Design decisions linked", _AWESOME,
         "The reasoning behind the design is not written down.", _decisions),
)


class ReadmeCritic:
    """Reads a README against every rule and says what is wrong, plainly."""

    def critique(self, root: Path) -> ReadmeReport:
        """Judge the README in `root`, or say that there is none."""
        path = _find_readme(Path(root))
        if path is None:
            missing = Gap(RULES[0], "no README file")
            return ReadmeReport(str(root), (missing,), (), (), (), "There is no README. The project has no front door.")
        return self._judge(path, parse(path))

    def critique_text(self, root: Path, name: str, text: str) -> ReadmeReport:
        """Judge README text that is not on disk yet, as if it were the file `name` in `root`."""
        path = Path(root) / name
        return self._judge(path, parse_text(path, text))

    def _judge(self, path: Path, readme: Readme) -> ReadmeReport:
        """Run every rule against one parsed README."""
        by_tier: dict[Tier, list[Gap]] = {tier: [] for tier in Tier}
        held: list[str] = []
        for rule in RULES:
            failure = rule.test(readme)
            if failure is None:
                held.append(f"{rule.id} {rule.name}")
            else:
                by_tier[rule.tier].append(Gap(rule, failure))
        failures, gaps, reach = (tuple(by_tier[t]) for t in (Tier.MINIMUM, Tier.STRONG, Tier.OVER_THE_TOP))
        return ReadmeReport(path.name, failures, gaps, reach, tuple(held), _verdict(failures, gaps, reach))


def _find_readme(root: Path) -> Optional[Path]:
    """The README in `root`, found ignoring case: README, .md, .markdown, .rst, .txt, in that order."""
    try:
        entries = [p for p in root.iterdir() if p.is_file()]
    except OSError:
        return None
    for wanted in ("readme", "readme.md", "readme.markdown", "readme.rst", "readme.txt"):
        match = sorted(p for p in entries if p.name.lower() == wanted)
        if match:
            return match[0]
    return None


def _verdict(failures: tuple[Gap, ...], gaps: tuple[Gap, ...], reach: tuple[Gap, ...]) -> str:
    if failures:
        return (f"This README fails the minimum: {len(failures)} thing(s) a reader needs are missing or broken. "
                "It is not ready to be someone's first impression.")
    if gaps:
        return (f"It meets the minimum and nothing more: {len(gaps)} strong-tier gap(s), "
                f"{len(reach)} short of over the top. Competent, forgettable.")
    if reach:
        return f"Solid. {len(reach)} thing(s) stand between this and over the top."
    return "Over the top. Every rule holds. Re-run it after every change; it will not stay that way by itself."
