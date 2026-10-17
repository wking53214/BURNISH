"""README claims that the tree itself contradicts: a pin, a dependency list, a test count.

The poetry critic compares a README to what the tree declares. Three kinds of
sentence went through it unchallenged until a person read them:

  * "pinned to Warden v0.11.0" while `pyproject.toml` pinned a different commit,
  * "No other dependencies" while the code imports and declares a second one,
  * "240 test cases" while the suite had 247, or any number nothing measured.

This module catches those three classes. It reads `pyproject.toml`, the imports
in the Python files, and the README prose. It runs nothing, and it counts no
tests: a test count is judged against a number somebody else collected (Warden,
or `pytest --collect-only` passed in as `collected`), and with no such number the
claim is reported as unverifiable, which is the honest answer.

WHAT IT DOES NOT OWN
    Counting or running tests (Warden and Ghost Tools), and fixing the README text.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Optional

from .claims import test_claims
from .files import find_readme, is_protected, python_files
from .marked import outside_fences, without_block
from .textsafe import clean

__all__ = ["Drift", "check_tree_claims", "check_test_claims", "readme_text_for_drift"]


@dataclass(frozen=True)
class Drift:
    """One README sentence the tree contradicts, or cannot support."""

    kind: str       # "pin", "dependencies" or "tests"
    claim: str      # the README's own words
    problem: str    # what is wrong, plainly
    verdict: str = "disagrees"   # "disagrees" (the tree says otherwise) or "unverifiable" (nothing measured backs it)

    def render(self) -> str:
        return f"{self.problem} (README: \"{self.claim}\")"


def readme_text_for_drift(readme: str) -> str:
    """The README as sentences to read: Burnish's block, fenced code and HTML comments gone, inline code unwrapped."""
    kept = without_block(readme)
    text = "\n".join(line for _, line in outside_fences(kept))
    return text.replace("`", "")


# ---------------------------------------------------------------- pins

_REF = r"(?P<ref>v?\d+\.\d+(?:\.\d+)?|(?=[0-9a-f]*\d)[0-9a-f]{7,40})"
_PIN_CLAIM = re.compile(
    rf"\bpinned\s+(?:(?:to|at)\s+(?:the\s+)?(?:[\w-]+\s+)?)?(?:(?:tag|release|version|commit|ref)\s+)?{_REF}\b", re.I)
_GIT_DEP = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)\s*(?:\[[^\]]*\])?\s*@\s*git\+[^@\s]+@(?P<ref>[^\s#;]+)")
_VERSION = re.compile(r"v?(\d+\.\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class _Pin:
    name: str
    ref: str
    tags: frozenset[str]   # versions the pin is known by: the ref itself if it is a tag, or a comment on its line


def _normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _project(root: Path) -> Optional[tuple[dict, str]]:
    """The parsed pyproject.toml and its text, or None if there is none or it cannot be read."""
    path = root / "pyproject.toml"
    try:
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
    except (OSError, ValueError):
        return None
    return data, text


def _dependency_strings(data: dict) -> list[str]:
    project = data.get("project")
    deps = project.get("dependencies") if isinstance(project, dict) else None
    out = [d for d in deps if isinstance(d, str)] if isinstance(deps, list) else []
    tool = data.get("tool")
    poetry = tool.get("poetry") if isinstance(tool, dict) else None
    table = poetry.get("dependencies") if isinstance(poetry, dict) else None
    if isinstance(table, dict):
        out += [name for name in table if name.lower() != "python"]
    return out


def _dependency_name(spec: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", spec)
    return _normal(match.group(1)) if match else ""


def _pins(data: dict, text: str) -> list[_Pin]:
    pins = []
    for spec in _dependency_strings(data):
        git = _GIT_DEP.match(spec)
        if not git:
            continue
        ref = git.group("ref")
        tags = set()
        if as_tag := _VERSION.fullmatch(ref):
            tags.add(as_tag.group(1))
        for line in text.splitlines():
            if ref in line and "#" in line.split(ref, 1)[1]:
                comment = line.split(ref, 1)[1].split("#", 1)[1]
                tags.update(m.group(1) for m in _VERSION.finditer(comment))
        pins.append(_Pin(_dependency_name(spec), ref, frozenset(tags)))
    return pins


def _describe(pin: _Pin) -> str:
    if _VERSION.fullmatch(pin.ref):
        return f"{pin.name} at tag {pin.ref}"
    recorded = f" (recorded as {', '.join(sorted(pin.tags))})" if pin.tags else " (no tag recorded)"
    return f"{pin.name} at commit {pin.ref[:7]}{recorded}"


def _pin_drift(text: str, pins: list[_Pin]) -> list[Drift]:
    out = []
    for match in _PIN_CLAIM.finditer(text):
        ref = match.group("ref")
        words = clean(match.group(0), 80)
        near = _normal(text[max(0, match.start() - 60):match.end()]).replace("-", " ")
        subject = [p for p in pins if p.name.replace("-", " ") in near] or pins
        if not subject:
            out.append(Drift("pin", words, "The README says something is pinned, but pyproject.toml pins no git dependency."))
            continue
        version = _VERSION.fullmatch(ref)
        if version:
            agrees = any(version.group(1) in pin.tags for pin in subject)
        else:
            agrees = any(pin.ref.startswith(ref.lower()) or ref.lower().startswith(pin.ref) for pin in subject)
        if not agrees:
            actual = "; ".join(_describe(p) for p in subject)
            out.append(Drift("pin", words, f"The README names a pin that pyproject.toml does not have: pyproject.toml pins {actual}. "
                                           "Point at pyproject.toml instead of restating the pin."))
    return out


# ---------------------------------------------------------------- dependencies

_NO_OTHER = re.compile(
    r"\bno\s+(?:other|further|additional|more|external|third[- ]party)\s+(?:runtime\s+)?dependenc(?:y|ies)\b"
    r"|\bno\s+(?:runtime\s+)?dependenc(?:y|ies)\b|\bzero[- ]dependenc(?:y|ies)\b|\bdependency[- ]free\b"
    r"|\b(?:standard[- ]library|stdlib)\s+only\b", re.I)
_QUOTED = re.compile(r"[\"'\u201c\u2018]\s*$")
_OTHER_WORD = re.compile(r"\b(?:other|further|additional|more)\b", re.I)


def _own_top_levels(root: Path) -> set[str]:
    names = set()
    for base in (root, root / "src"):
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir() and (child / "__init__.py").is_file():
                    names.add(child.name)
                elif child.suffix == ".py":
                    names.add(child.stem)
    return names


def _imported(root: Path) -> dict[str, int]:
    """Third-party top-level modules imported by the target's own non-test code, and in how many files."""
    own = _own_top_levels(root)
    counts: dict[str, int] = {}
    for path in python_files(root):
        relative = path.relative_to(root).as_posix()
        if is_protected(relative):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError, RecursionError, MemoryError):
            continue
        seen: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                seen.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                seen.add(node.module.split(".")[0])
        for name in seen:
            if name not in sys.stdlib_module_names and name not in own and name != "__future__":
                counts[name] = counts.get(name, 0) + 1
    return counts


def _distribution_of(module: str, declared: set[str]) -> str:
    """The declared distribution a module belongs to, by installed metadata or by name; else the module's own name."""
    try:
        owners = metadata.packages_distributions().get(module, [])
    except (OSError, ValueError):
        owners = []
    return next((_normal(dist) for dist in owners if _normal(dist) in declared), _normal(module))


def _paragraph(text: str, position: int) -> str:
    start = text.rfind("\n\n", 0, position) + 2
    end = text.find("\n\n", position)
    return text[max(start, 0):end if end >= 0 else len(text)]


def _dependency_drift(root: Path, text: str, data: dict) -> list[Drift]:
    claims = list(_NO_OTHER.finditer(text))
    if not claims:
        return []
    declared = {n for n in map(_dependency_name, _dependency_strings(data)) if n}
    imported = _imported(root)
    files_using: dict[str, int] = {}
    for module, files in imported.items():
        dist = _distribution_of(module, declared)
        files_using[dist] = max(files_using.get(dist, 0), files)
    actual = declared | set(files_using)
    out = []
    for claim in claims:
        if _QUOTED.search(text[max(0, claim.start() - 2):claim.start()]):
            continue   # the phrase is being mentioned in quotation marks, not asserted
        paragraph = _normal(_paragraph(text, claim.start())).replace("-", " ")
        named = {n for n in actual if re.search(rf"\b{re.escape(n.replace('-', ' '))}\b", paragraph)}
        if not _OTHER_WORD.search(claim.group(0)):
            named = set()   # "no dependencies" leaves nothing out
        unnamed = sorted(actual - named)
        if not unnamed:
            continue
        details = []
        for name in unnamed:
            facts = ["declared in pyproject.toml"] if name in declared else []
            if name in files_using:
                facts.append(f"imported in {files_using[name]} file(s)" + ("" if name in declared else ", not declared"))
            details.append(f"{name} ({', '.join(facts)})")
        out.append(Drift("dependencies", clean(claim.group(0), 60),
                         "The README says there are no dependencies beyond the ones it names, but the tree also has: "
                         + ", ".join(details) + "."))
    return out


# ---------------------------------------------------------------- tests

def check_test_claims(readme: str, collected: Optional[int] = None) -> list[Drift]:
    """README test counts with nothing measured behind them, or that disagree with a collected count.

    `collected` is the number a test runner reported for the suite (for example the total from
    `pytest --collect-only -q`). Without it every numeric claim is unverifiable here: Burnish counts no tests.
    A claim that tests pass is never confirmed by a collected count; only a count that cannot be true is refuted.
    """
    out = []
    for claim in test_claims(readme):
        if claim.kind == "green":
            continue
        words = clean(claim.text, 80)
        if collected is None:
            out.append(Drift("tests", words, f"The README states a count of {claim.number} for the suite, and no measurement backs "
                                             "it: Burnish counts no tests. Drop the number, or pass the collected count "
                                             "(--collected), or run the finisher through Warden.", "unverifiable"))
            continue
        if claim.at_least:
            wrong = collected < claim.number
        elif claim.kind == "count":
            wrong = claim.number != collected
        else:   # says they pass: more passing than collected is impossible, and "N/M" names the whole suite
            wrong = claim.number > collected or (claim.total is not None and claim.total != collected)
        if wrong:
            out.append(Drift("tests", words, f"The README states a count of {claim.number}; the suite collects {collected}. "
                                             "These disagree."))
    return out


# ---------------------------------------------------------------- entry point

def check_tree_claims(root: Path, readme: Optional[str] = None) -> list[Drift]:
    """Pin and dependency claims in the README of `root` that its pyproject.toml and imports contradict.

    `readme` is the README text to judge; by default it is read from `root`. A tree with no pyproject.toml
    or no README has nothing to contradict.
    """
    root = Path(root)
    if readme is None:
        path = find_readme(root)
        if path is None:
            return []
        readme = path.read_text(encoding="utf-8", errors="replace")
    project = _project(root)
    if project is None:
        return []
    data, raw = project
    text = readme_text_for_drift(readme)
    return _pin_drift(text, _pins(data, raw)) + _dependency_drift(root, text, data)
