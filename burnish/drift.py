"""README claims that the tree itself contradicts: a pin, a dependency list, a test count.

The poetry critic compares a README to what the tree declares. Three kinds of
sentence went through it unchallenged until a person read them:

  * "pinned to Warden v0.11.0" while `pyproject.toml` pinned a different commit,
  * "No other dependencies" while the code imports and declares a second one,
  * "240 test cases" while the suite had 247, or any number nothing measured.

A pin or a dependency declared only in an optional dependency (`[project.optional-dependencies]`, `[dependency-groups]`,
Poetry's groups) is read too: a claim it backs is not a contradiction, and `claims_held_by_extras` says so. A module imported
only inside a function, behind a `try` that expects the import to fail, or under `TYPE_CHECKING` is optional as well.

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

__all__ = ["Drift", "check_tree_claims", "claims_held_by_extras", "check_test_claims", "readme_text_for_drift"]


@dataclass(frozen=True)
class Drift:
    """One README sentence the tree contradicts, or cannot support."""

    kind: str       # "pin", "dependencies" or "tests"
    claim: str      # the README's own words
    problem: str    # what is wrong, plainly
    #: "disagrees" (the tree says otherwise), "unverifiable" (nothing measured backs it) or "extra" (the claim holds, but
    #: only because pyproject.toml declares the thing as an optional dependency; see `claims_held_by_extras`).
    verdict: str = "disagrees"

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
    where: str = ""        # "" for a runtime dependency, else "extra NAME" or "group NAME"


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


def _optional_strings(data: dict) -> list[tuple[str, str]]:
    """(where, requirement) for every optional dependency: `[project.optional-dependencies]`, PEP 735 `[dependency-groups]`
    and Poetry's dependency groups. A group that includes another group (`{include-group = ...}`) is read through the other."""
    out: list[tuple[str, str]] = []
    project = data.get("project")
    extras = project.get("optional-dependencies") if isinstance(project, dict) else None
    if isinstance(extras, dict):
        for name, specs in extras.items():
            if isinstance(specs, list):
                out += [(f"extra {name}", s) for s in specs if isinstance(s, str)]
    groups = data.get("dependency-groups")
    if isinstance(groups, dict):
        for name, specs in groups.items():
            if isinstance(specs, list):
                out += [(f"group {name}", s) for s in specs if isinstance(s, str)]
    tool = data.get("tool")
    poetry = tool.get("poetry") if isinstance(tool, dict) else None
    poetry_groups = poetry.get("group") if isinstance(poetry, dict) else None
    if isinstance(poetry_groups, dict):
        for name, body in poetry_groups.items():
            table = body.get("dependencies") if isinstance(body, dict) else None
            if isinstance(table, dict):
                out += [(f"group {name}", dep) for dep in table if dep.lower() != "python"]
    return out


def _dependency_name(spec: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", spec)
    return _normal(match.group(1)) if match else ""


def _pins(data: dict, text: str) -> list[_Pin]:
    pins = []
    for where, spec in [("", s) for s in _dependency_strings(data)] + _optional_strings(data):
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
        pins.append(_Pin(_dependency_name(spec), ref, frozenset(tags), where))
    return pins


def _describe(pin: _Pin) -> str:
    where = f" in {pin.where}" if pin.where else ""
    if _VERSION.fullmatch(pin.ref):
        return f"{pin.name} at tag {pin.ref}{where}"
    recorded = f" (recorded as {', '.join(sorted(pin.tags))})" if pin.tags else " (no tag recorded)"
    return f"{pin.name} at commit {pin.ref[:7]}{recorded}{where}"


def _agrees(pin: _Pin, ref: str) -> bool:
    """True when the README's `ref` (a release or a commit prefix) names this pin."""
    version = _VERSION.fullmatch(ref)
    if version:
        return version.group(1) in pin.tags
    return pin.ref.startswith(ref.lower()) or ref.lower().startswith(pin.ref)


def _pin_drift(text: str, pins: list[_Pin]) -> tuple[list[Drift], list[Drift]]:
    """(claims the pins contradict, claims that hold only because a pin sits in an optional dependency)."""
    out: list[Drift] = []
    held: list[Drift] = []
    for match in _PIN_CLAIM.finditer(text):
        ref = match.group("ref")
        words = clean(match.group(0), 80)
        near = _normal(text[max(0, match.start() - 60):match.end()]).replace("-", " ")
        subject = [p for p in pins if p.name.replace("-", " ") in near] or pins
        if not subject:
            out.append(Drift("pin", words, "The README says something is pinned, but pyproject.toml pins no git dependency."))
            continue
        matching = [pin for pin in subject if _agrees(pin, ref)]
        if any(not pin.where for pin in matching):
            continue
        if matching:
            places = ", ".join(sorted({pin.where for pin in matching}))
            held.append(Drift("pin", words, "The README names a pin that pyproject.toml has only in an optional dependency "
                                            f"({places}); it is not a runtime dependency, so the claim holds for that extra only.",
                              "extra"))
            continue
        actual = "; ".join(_describe(p) for p in subject)
        out.append(Drift("pin", words, f"The README names a pin that pyproject.toml does not have: pyproject.toml pins {actual}. "
                                       "Point at pyproject.toml instead of restating the pin."))
    return out, held


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


_EXPECTS_IT_MAY_FAIL = frozenset({"ImportError", "ModuleNotFoundError", "Exception", "BaseException"})


def _catches_a_failed_import(handler: ast.ExceptHandler) -> bool:
    """True for `except:` and for a handler that names ImportError, ModuleNotFoundError, Exception or BaseException."""
    if handler.type is None:
        return True
    named = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(isinstance(n, ast.Name) and n.id in _EXPECTS_IT_MAY_FAIL for n in named)


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def _modules_imported(tree: ast.AST) -> tuple[set[str], set[str]]:
    """(modules imported when the file is loaded, modules imported only later or only if they can be).

    An import inside a function, in a `try` that expects the import to fail, or under `if TYPE_CHECKING:` is optional: the
    file loads without it. The walk is iterative, because a file can nest an expression deeper than Python's recursion limit.
    """
    hard: set[str] = set()
    lazy: set[str] = set()
    stack: list[tuple[ast.AST, bool]] = [(tree, False)]
    while stack:
        node, optional = stack.pop()
        if isinstance(node, ast.Import):
            (lazy if optional else hard).update(alias.name.split(".")[0] for alias in node.names)
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                (lazy if optional else hard).add(node.module.split(".")[0])
            continue
        inherits = optional or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        body_optional = inherits
        if isinstance(node, (ast.Try, ast.TryStar)) and any(_catches_a_failed_import(h) for h in node.handlers):
            body_optional = True
        elif isinstance(node, ast.If) and _is_type_checking(node.test):
            body_optional = True
        for field, value in ast.iter_fields(node):
            children = value if isinstance(value, list) else [value]
            for child in children:
                if isinstance(child, ast.AST):
                    stack.append((child, body_optional if field == "body" else inherits))
    return hard, lazy


def _imported(root: Path) -> tuple[dict[str, int], dict[str, int]]:
    """Third-party top-level modules the target's own non-test code imports, and in how many files.

    Two tables: modules the code needs to load, and modules it imports only optionally (inside a function, behind a
    `try` that expects the import to fail, or under `TYPE_CHECKING`). A module in both is in the first.
    """
    own = _own_top_levels(root)
    hard_counts: dict[str, int] = {}
    lazy_counts: dict[str, int] = {}
    for path in python_files(root):
        relative = path.relative_to(root).as_posix()
        if is_protected(relative):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError, RecursionError, MemoryError):
            continue
        hard, lazy = _modules_imported(tree)
        for names, counts in ((hard, hard_counts), (lazy - hard, lazy_counts)):
            for name in names:
                if name not in sys.stdlib_module_names and name not in own and name != "__future__":
                    counts[name] = counts.get(name, 0) + 1
    return hard_counts, lazy_counts


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


def _dependency_drift(root: Path, text: str, data: dict) -> tuple[list[Drift], list[Drift]]:
    """(claims the tree contradicts, claims that hold only because the thing is declared as an optional dependency)."""
    claims = list(_NO_OTHER.finditer(text))
    if not claims:
        return [], []
    declared = {n for n in map(_dependency_name, _dependency_strings(data)) if n}
    optional = {name: where for where, spec in _optional_strings(data) if (name := _dependency_name(spec))}
    known = declared | set(optional)
    hard_imports, _ = _imported(root)
    files_using: dict[str, int] = {}
    for module, files in hard_imports.items():
        dist = _distribution_of(module, known)
        files_using[dist] = max(files_using.get(dist, 0), files)
    actual = declared | set(files_using)
    out: list[Drift] = []
    held: list[Drift] = []
    seen: set[str] = set()
    for claim in claims:
        if _QUOTED.search(text[max(0, claim.start() - 2):claim.start()]):
            continue   # the phrase is being mentioned in quotation marks, not asserted
        paragraph = _normal(_paragraph(text, claim.start())).replace("-", " ")
        named = {n for n in actual if re.search(rf"\b{re.escape(n.replace('-', ' '))}\b", paragraph)}
        if not _OTHER_WORD.search(claim.group(0)):
            named = set()   # "no dependencies" leaves nothing out
        unnamed = sorted(actual - named)
        only_optional = [n for n in unnamed if n not in declared and n in optional]
        against = [n for n in unnamed if n not in only_optional]
        details = []
        for name in against:
            facts = ["declared in pyproject.toml"] if name in declared else []
            if name in files_using:
                facts.append(f"imported in {files_using[name]} file(s)" + ("" if name in declared else ", not declared"))
            details.append(f"{name} ({', '.join(facts)})")
        if details:
            problem, bucket, verdict = ("The README says there are no dependencies beyond the ones it names, but the tree also has: "
                                        + ", ".join(details) + "."), out, "disagrees"
        elif only_optional:
            places = ", ".join(f"{n} ({optional[n]})" for n in only_optional)
            problem, bucket, verdict = ("The README says there are no dependencies beyond the ones it names; the tree also "
                                        f"imports {places}, which pyproject.toml declares only as an optional dependency, not "
                                        "as a runtime dependency. The claim holds for runtime dependencies."), held, "extra"
        else:
            continue
        if problem not in seen:   # two phrasings of one claim ("no runtime dependencies", "no runtime dependency") are one note
            seen.add(problem)
            bucket.append(Drift("dependencies", clean(claim.group(0), 60), problem, verdict))
    return out, held


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

def _tree_claims(root: Path, readme: Optional[str]) -> tuple[list[Drift], list[Drift]]:
    """(claims pyproject.toml and the imports contradict, claims they back only through an optional dependency)."""
    root = Path(root)
    if readme is None:
        path = find_readme(root)
        if path is None:
            return [], []
        readme = path.read_text(encoding="utf-8", errors="replace")
    project = _project(root)
    if project is None:
        return [], []
    data, raw = project
    text = readme_text_for_drift(readme)
    pin_against, pin_held = _pin_drift(text, _pins(data, raw))
    dep_against, dep_held = _dependency_drift(root, text, data)
    return _unique(pin_against + dep_against), _unique(pin_held + dep_held)


def _unique(drifts: list[Drift]) -> list[Drift]:
    """The drifts with a repeated note dropped: the same problem found in two sentences is told once."""
    seen: set[tuple[str, str]] = set()
    out = []
    for drift in drifts:
        if (drift.kind, drift.problem) not in seen:
            seen.add((drift.kind, drift.problem))
            out.append(drift)
    return out


def check_tree_claims(root: Path, readme: Optional[str] = None) -> list[Drift]:
    """Pin and dependency claims in the README of `root` that its pyproject.toml and imports contradict.

    `readme` is the README text to judge; by default it is read from `root`. A tree with no pyproject.toml
    or no README has nothing to contradict. Pins and dependencies in `[project.optional-dependencies]` and
    `[dependency-groups]` are read too, and a module imported only inside a function or behind a `try` that expects
    the import to fail is optional: neither makes a claim false.
    """
    return _tree_claims(root, readme)[0]


def claims_held_by_extras(root: Path, readme: Optional[str] = None) -> list[Drift]:
    """Claims that are true, but only because pyproject.toml declares the thing as an optional dependency.

    "Pinned to CNS v2.0.0" while the pin sits in an extra, or "no runtime dependencies" while a module that needs an extra
    is imported. They are not contradictions (`check_tree_claims` leaves them out); a reader is told why they hold.
    """
    return _tree_claims(root, readme)[1]
