"""README claims that the tree itself contradicts: a pin, a dependency list, a test count.

The poetry critic compares a README to what the tree declares. Three kinds of
sentence went through it unchallenged until a person read them:

  * "pinned to Warden v0.11.0" while `pyproject.toml` pinned a different commit,
  * "No other dependencies" while the code imports and declares a second one,
  * "240 test cases" while the suite had 247, or any number nothing measured.

A pin or a dependency declared only in an optional dependency (`[project.optional-dependencies]`, `[dependency-groups]`,
Poetry's groups) is read too: a claim it backs is not a contradiction, and `claims_held_by_extras` says so. A module imported
behind a `try` that expects the import to fail, or under `TYPE_CHECKING`, is optional: the code runs without it. A module
imported inside a function is not: the function may run on every use, and nothing here can tell. If pyproject.toml does not
declare it, a claim of no dependencies is reported as not confirmed (verdict "unconfirmed"), neither held nor contradicted.

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
from .files import find_readme, is_protected, pyproject_problem_at, python_files
from .marked import prose_lines
from .provenance import Basis, Provenance, Source
from .textsafe import clean

__all__ = ["Drift", "check_tree_claims", "claims_held_by_extras", "check_test_claims", "readme_text_for_drift"]


@dataclass(frozen=True)
class Drift:
    """One README sentence the tree contradicts, or cannot support."""

    kind: str       # "pin", "dependencies" or "tests"
    claim: str      # the README's own words
    problem: str    # what is wrong, plainly
    #: "disagrees" (the tree says otherwise), "unverifiable" (nothing measured backs it), "unchecked" (pyproject.toml is
    #: there but cannot be parsed, so the claim was not compared with it), "unconfirmed" (the code imports an undeclared
    #: module inside a function, which may or may not run on every use) or "extra" (the claim holds, but only because
    #: pyproject.toml declares the thing as an optional dependency; see `claims_held_by_extras`).
    verdict: str = "disagrees"
    #: The line of the README text the claim was read from, counting from 1 (0 when not known).
    line: int = 0
    #: Where the verdict comes from: the evidence, the method, what was not inspected. Its `claim_at` is the README line in
    #: the text given, with the path "README"; the critic names the file.
    provenance: Optional[Provenance] = None

    def render(self) -> str:
        return f"{self.problem} (README: \"{self.claim}\")"


def readme_text_for_drift(readme: str) -> str:
    """The README as sentences to read: Burnish's block, fenced code and HTML comments gone, inline code unwrapped."""
    return _drift_text(readme)[0]


def _drift_text(readme: str) -> tuple[str, list[int]]:
    """`readme_text_for_drift`, and for each of its lines the number of the README line it came from."""
    kept = prose_lines(readme)
    return "\n".join(line for _, line in kept).replace("`", ""), [number for number, _ in kept]


def _line_at(text: str, lines: list[int], offset: int) -> int:
    """The README line that `offset` in the drift text came from, or 0."""
    index = text.count("\n", 0, offset)
    return lines[index] if index < len(lines) else 0


def _line_of(text: str, needle: str) -> int:
    """The first line of `text` that holds `needle` and is not a comment line, counting from 1, or 0."""
    if needle:
        for number, line in enumerate(text.splitlines(), 1):
            if needle in line and not line.lstrip().startswith("#"):
                return number
    return 0


def _provenance(words: str, line: int, evidence: tuple[Source, ...], method: str, basis: Basis,
                not_inspected: tuple[str, ...], reason: str) -> Provenance:
    return Provenance(claim=f'"{words}"', claim_at=Source("README", line), evidence=evidence, method=method, basis=basis,
                      not_inspected=not_inspected, reason=reason)


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
    line: int = 0          # the line of pyproject.toml that declares it


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
        pins.append(_Pin(_dependency_name(spec), ref, frozenset(tags), where, _line_of(text, spec) or _line_of(text, ref)))
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


_PIN_METHOD = ("Read every git dependency in pyproject.toml (runtime, optional and group) and compared the release or commit "
               "the README names with each pin's ref, and with any version written in a comment on the pin's line.")
_PIN_NOT_INSPECTED = ("whether a pinned commit is the release the README names: no tag or commit was fetched, so a release "
                      "counts only when it is the ref itself or is written in a comment on the pin's line",
                      "lock files and the packages actually installed")


def _pin_source(pin: _Pin) -> Source:
    return Source("pyproject.toml", pin.line, f"git pin {_describe(pin)}")


def _pin_drift(text: str, lines: list[int], pins: list[_Pin]) -> tuple[list[Drift], list[Drift]]:
    """(claims the pins contradict, claims that hold only because a pin sits in an optional dependency)."""
    out: list[Drift] = []
    held: list[Drift] = []
    for match in _PIN_CLAIM.finditer(text):
        ref = match.group("ref")
        words = clean(match.group(0), 80)
        line = _line_at(text, lines, match.start())
        near = _normal(text[max(0, match.start() - 60):match.end()]).replace("-", " ")
        named = [p for p in pins if p.name.replace("-", " ") in near]
        subject = named or pins
        method = _PIN_METHOD if named or not subject else (
            _PIN_METHOD + " The sentence names no pinned dependency, so it was compared with every pin.")
        basis: Basis = "direct" if named or not subject else "inferred"
        if not subject:
            problem = "The README says something is pinned, but pyproject.toml pins no git dependency."
            evidence = (Source("pyproject.toml", 0, "no git dependency in its dependencies, optional dependencies or groups"),)
            out.append(Drift("pin", words, problem, "disagrees", line,
                             _provenance(words, line, evidence, method, basis, _PIN_NOT_INSPECTED, problem)))
            continue
        matching = [pin for pin in subject if _agrees(pin, ref)]
        if any(not pin.where for pin in matching):
            continue
        if matching:
            places = ", ".join(sorted({pin.where for pin in matching}))
            problem = ("The README names a pin that pyproject.toml has only in an optional dependency "
                       f"({places}); it is not a runtime dependency, so the claim holds for that extra only.")
            held.append(Drift("pin", words, problem, "extra", line,
                              _provenance(words, line, tuple(map(_pin_source, matching)), method, basis,
                                          _PIN_NOT_INSPECTED, problem)))
            continue
        actual = "; ".join(_describe(p) for p in subject)
        problem = (f"The README names a pin that pyproject.toml does not have: pyproject.toml pins {actual}. "
                   "Point at pyproject.toml instead of restating the pin.")
        out.append(Drift("pin", words, problem, "disagrees", line,
                         _provenance(words, line, tuple(map(_pin_source, subject)), method, basis,
                                     _PIN_NOT_INSPECTED, problem)))
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


def _modules_imported(tree: ast.AST) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """(modules imported when the file is loaded, modules imported inside a function, modules imported only if they can be),
    each module with the first line that imports it that way.

    An import behind a `try` that expects the import to fail, or under `if TYPE_CHECKING:`, is guarded: the code runs
    without it. An import inside a function is deferred, not optional: the function may run on every use. A guard wins
    over a function. The walk is iterative, because a file can nest an expression deeper than Python's recursion limit.
    """
    hard: dict[str, int] = {}
    deferred: dict[str, int] = {}
    guarded: dict[str, int] = {}
    stack: list[tuple[ast.AST, bool, bool]] = [(tree, False, False)]
    while stack:
        node, in_function, in_guard = stack.pop()
        bucket = guarded if in_guard else deferred if in_function else hard
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                bucket[name] = min(bucket.get(name, node.lineno), node.lineno)
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                name = node.module.split(".")[0]
                bucket[name] = min(bucket.get(name, node.lineno), node.lineno)
            continue
        function = in_function or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        body_guard = in_guard
        if isinstance(node, (ast.Try, ast.TryStar)) and any(_catches_a_failed_import(h) for h in node.handlers):
            body_guard = True
        elif isinstance(node, ast.If) and _is_type_checking(node.test):
            body_guard = True
        for field, value in ast.iter_fields(node):
            children = value if isinstance(value, list) else [value]
            for child in children:
                if isinstance(child, ast.AST):
                    stack.append((child, function, body_guard if field == "body" else in_guard))
    return hard, deferred, guarded


@dataclass
class _Imports:
    """Third-party top-level modules the target's own non-test code imports: in how many files, and where first.

    Three tables: modules the code needs to load, modules it imports inside a function, and modules it imports only
    behind a guard (a `try` that expects the import to fail, or `TYPE_CHECKING`). A module is counted once per file, in
    the first of the three that holds it there. `at` gives, per table, the first file and line that import each module.
    `unread` lists the files that could not be parsed, whose imports were therefore not read.
    """

    hard: dict[str, int]
    deferred: dict[str, int]
    guarded: dict[str, int]
    at: dict[str, dict[str, tuple[str, int]]]
    unread: list[str]


def _imported(root: Path) -> _Imports:
    """What `_Imports` describes, for the tree at `root`."""
    own = _own_top_levels(root)
    found = _Imports({}, {}, {}, {"hard": {}, "deferred": {}, "guarded": {}}, [])
    for path in python_files(root):
        relative = path.relative_to(root).as_posix()
        if is_protected(relative):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError, RecursionError, MemoryError):
            found.unread.append(relative)
            continue
        hard, deferred, guarded = _modules_imported(tree)
        tables = (("hard", hard, found.hard), ("deferred", {n: at for n, at in deferred.items() if n not in hard},
                                                found.deferred),
                  ("guarded", {n: at for n, at in guarded.items() if n not in hard and n not in deferred}, found.guarded))
        for table, names, counts in tables:
            for name, line in names.items():
                if name not in sys.stdlib_module_names and name not in own and name != "__future__":
                    counts[name] = counts.get(name, 0) + 1
                    found.at[table].setdefault(name, (relative, line))
    return found


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


_DEPENDENCY_METHOD = ("Listed the runtime dependencies pyproject.toml declares and the third-party modules the non-test Python "
                      "files import (the standard library and the project's own packages left out), matched each module "
                      "to a package by the installed package metadata or by its name, and set aside the ones the README "
                      "names in the same paragraph.")


def _dependency_not_inspected(unread: list[str], deferred: bool) -> tuple[str, ...]:
    out = ["test files, test settings, CI and Ghost files: their imports are not read",
           "whether an import behind a guard (a try that expects it to fail, or TYPE_CHECKING) is ever needed: it counts "
           "as optional",
           "modules imported at run time by name (importlib, __import__)"]
    if deferred:
        out.append("whether the function that holds the import runs on every use")
    if unread:
        shown = ", ".join(clean(path) for path in unread[:5]) + (" and more" if len(unread) > 5 else "")
        out.append(f"the imports of {len(unread)} file(s) that could not be parsed: {shown}")
    return tuple(out)


def _dependency_drift(root: Path, text: str, lines: list[int], data: dict, raw: str) -> tuple[list[Drift], list[Drift]]:
    """(claims the tree contradicts, claims that hold only because the thing is declared as an optional dependency)."""
    claims = list(_NO_OTHER.finditer(text))
    if not claims:
        return [], []
    declared_at = {name: _line_of(raw, spec) for spec in _dependency_strings(data) if (name := _dependency_name(spec))}
    declared = set(declared_at)
    optional = {name: where for where, spec in _optional_strings(data) if (name := _dependency_name(spec))}
    optional_at = {name: _line_of(raw, spec) for _, spec in _optional_strings(data) if (name := _dependency_name(spec))}
    known = declared | set(optional)
    imports = _imported(root)
    files_using: dict[str, int] = {}
    used_at: dict[str, tuple[str, str, int]] = {}   # package -> (module, file, line) of the first import
    for module, files in imports.hard.items():
        dist = _distribution_of(module, known)
        files_using[dist] = max(files_using.get(dist, 0), files)
        used_at.setdefault(dist, (module, *imports.at["hard"][module]))
    actual = declared | set(files_using)
    #: Undeclared modules imported only inside a function: the claim may be true, and nothing here can show it.
    deferred_using: dict[str, int] = {}
    deferred_at: dict[str, tuple[str, str, int]] = {}
    for module, files in imports.deferred.items():
        dist = _distribution_of(module, known)
        if dist not in known and dist not in actual:
            deferred_using[dist] = max(deferred_using.get(dist, 0), files)
            deferred_at.setdefault(dist, (module, *imports.at["deferred"][module]))

    def declared_source(name: str) -> Source:
        return Source("pyproject.toml", declared_at.get(name, 0), f"declares {name} as a runtime dependency")

    def import_source(name: str, where: dict[str, tuple[str, str, int]], how: str) -> Source:
        module, path, line = where[name]
        return Source(clean(path), line, f"imports {module}{how}")

    out: list[Drift] = []
    held: list[Drift] = []
    seen: set[str] = set()
    for claim in claims:
        if _QUOTED.search(text[max(0, claim.start() - 2):claim.start()]):
            continue   # the phrase is being mentioned in quotation marks, not asserted
        paragraph = _normal(_paragraph(text, claim.start())).replace("-", " ")
        named = {n for n in actual | set(deferred_using) if re.search(rf"\b{re.escape(n.replace('-', ' '))}\b", paragraph)}
        if not _OTHER_WORD.search(claim.group(0)):
            named = set()   # "no dependencies" leaves nothing out
        unnamed = sorted(actual - named)
        unconfirmed = sorted(set(deferred_using) - named)
        only_optional = [n for n in unnamed if n not in declared and n in optional]
        against = [n for n in unnamed if n not in only_optional]
        details = []
        for name in against:
            facts = ["declared in pyproject.toml"] if name in declared else []
            if name in files_using:
                facts.append(f"imported in {files_using[name]} file(s)" + ("" if name in declared else ", not declared"))
            details.append(f"{name} ({', '.join(facts)})")
        evidence: list[Source] = []
        basis: Basis = "inferred"
        if details:
            problem, bucket, verdict = ("The README says there are no dependencies beyond the ones it names, but the tree also has: "
                                        + ", ".join(details) + "."), out, "disagrees"
            for name in against:
                if name in declared:
                    evidence.append(declared_source(name))
                if name in used_at:
                    evidence.append(import_source(name, used_at, ""))
            #: A declared package is stated by pyproject.toml itself; an undeclared one is known only through a module name.
            basis = "direct" if all(name in declared for name in against) else "inferred"
        elif only_optional:
            places = ", ".join(f"{n} ({optional[n]})" for n in only_optional)
            problem, bucket, verdict = ("The README says there are no dependencies beyond the ones it names; the tree also "
                                        f"imports {places}, which pyproject.toml declares only as an optional dependency, not "
                                        "as a runtime dependency. The claim holds for runtime dependencies."), held, "extra"
            for name in only_optional:
                evidence.append(Source("pyproject.toml", optional_at.get(name, 0), f"declares {name} in {optional[name]}"))
                evidence.append(import_source(name, used_at, ""))
        elif unconfirmed:
            places = ", ".join(f"{n} (imported inside a function in {deferred_using[n]} file(s), not declared)"
                               for n in unconfirmed)
            problem, bucket, verdict = ("The README says there are no dependencies beyond the ones it names; the code also "
                                        f"imports {places}. Whether that code runs on every use was not checked, so the claim "
                                        "is not confirmed. Declare the module in pyproject.toml (as a runtime or an optional "
                                        "dependency) or name it in the README."), out, "unconfirmed"
            evidence = [import_source(name, deferred_at, " inside a function") for name in unconfirmed]
        else:
            continue
        if problem not in seen:   # two phrasings of one claim ("no runtime dependencies", "no runtime dependency") are one note
            seen.add(problem)
            words = clean(claim.group(0), 60)
            line = _line_at(text, lines, claim.start())
            bucket.append(Drift("dependencies", words, problem, verdict, line,
                                _provenance(words, line, tuple(evidence), _DEPENDENCY_METHOD, basis,
                                            _dependency_not_inspected(imports.unread, verdict == "unconfirmed"), problem)))
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
            problem = (f"The README states a count of {claim.number} for the suite, and no measurement backs it: Burnish "
                       "counts no tests. Drop the number, or pass the collected count (--collected), or run the finisher "
                       "through Warden.")
            out.append(Drift("tests", words, problem, "unverifiable", claim.line,
                             _provenance(words, claim.line, (), _NOTHING_MEASURED, "none", _SUITE_NOT_READ, problem)))
            continue
        if claim.at_least:
            wrong = collected < claim.number
        elif claim.kind == "count":
            wrong = claim.number != collected
        else:   # says they pass: more passing than collected is impossible, and "N/M" names the whole suite
            wrong = claim.number > collected or (claim.total is not None and claim.total != collected)
        given = (Source("", 0, f"the collected count given with --collected ({collected})"),)
        if wrong:
            problem = f"The README states a count of {claim.number}; the suite collects {collected}. These disagree."
            out.append(Drift("tests", words, problem, "disagrees", claim.line,
                             _provenance(words, claim.line, given, _COLLECTED_METHOD, "direct", _COLLECTED_NOT_READ, problem)))
        elif claim.kind == "passing":
            problem = (f"The README says {claim.number} tests pass; the suite collects {collected}, which allows it, but "
                       "whether they pass was not measured here. Run the finisher through Warden for a measured result.")
            out.append(Drift("tests", words, problem, "unverifiable", claim.line,
                             _provenance(words, claim.line, given, _COLLECTED_METHOD, "direct", _COLLECTED_NOT_READ, problem)))
    return out


_NOTHING_MEASURED = ("Looked for a measured count to compare with: none was handed in (no suite result from Warden and no "
                     "--collected count).")
_SUITE_NOT_READ = ("the suite itself: Burnish counts and runs no tests",)
_COLLECTED_METHOD = ("Compared the README's number with the collected count: an 'at least' figure must not exceed it, a bare "
                     "count must equal it, a count said to pass must not exceed it, and the second number of an N/M figure "
                     "must equal it.")
_COLLECTED_NOT_READ = ("whether the collected tests pass: a collected count is a count, not a result",
                       "which tests were collected: only the total was given")


# ---------------------------------------------------------------- entry point

def _tree_claims(root: Path, readme: Optional[str]) -> tuple[list[Drift], list[Drift]]:
    """(claims pyproject.toml and the imports contradict, claims they back only through an optional dependency)."""
    root = Path(root)
    if readme is None:
        path = find_readme(root)
        if path is None:
            return [], []
        readme = path.read_text(encoding="utf-8", errors="replace")
    text, lines = _drift_text(readme)
    problem, problem_line = pyproject_problem_at(root)
    if problem is not None:
        return _unchecked(text, lines, problem, problem_line), []
    project = _project(root)
    if project is None:
        return [], []
    data, raw = project
    pin_against, pin_held = _pin_drift(text, lines, _pins(data, raw))
    dep_against, dep_held = _dependency_drift(root, text, lines, data, raw)
    return _unique(pin_against + dep_against), _unique(pin_held + dep_held)


def _unchecked(text: str, lines: list[int], problem: str, problem_line: int) -> list[Drift]:
    """One "unchecked" drift for each kind of claim (a pin, a dependency list) the README makes, when pyproject.toml is broken.

    The claim may be true. It is not reported as held, because the only file that could back it was not read.
    """
    out = []
    pins = list(_PIN_CLAIM.finditer(text))
    deps = [m for m in _NO_OTHER.finditer(text) if not _QUOTED.search(text[max(0, m.start() - 2):m.start()])]
    for kind, matches in (("pin", pins), ("dependencies", deps)):
        if matches:
            words = clean(matches[0].group(0), 80)
            line = _line_at(text, lines, matches[0].start())
            note = (f"{problem}, so this {'pin' if kind == 'pin' else 'dependency'} claim was not checked against it. "
                    "Fix pyproject.toml and run the critic again.")
            out.append(Drift(kind, words, note, "unchecked", line, _provenance(
                words, line, (Source("pyproject.toml", problem_line, problem),),
                "Parsed pyproject.toml as TOML with Python's tomllib; it failed, so nothing was compared.", "direct",
                (f"every {'pin' if kind == 'pin' else 'dependency'} pyproject.toml declares: the file did not parse, so the "
                 "claim was not compared with it",), note)))
    return out


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
    or no README has nothing to contradict. A pyproject.toml that is there but cannot be parsed backs nothing: each
    kind of claim the README makes comes back once with the verdict "unchecked". Pins and dependencies in
    `[project.optional-dependencies]` and `[dependency-groups]` are read too, and a module imported behind a `try` that
    expects the import to fail is optional: neither makes a claim false. An undeclared module imported inside a function
    makes a claim of no dependencies "unconfirmed": it is listed here, because nothing shows the claim holds.
    """
    return _tree_claims(root, readme)[0]


def claims_held_by_extras(root: Path, readme: Optional[str] = None) -> list[Drift]:
    """Claims that are true, but only because pyproject.toml declares the thing as an optional dependency.

    "Pinned to CNS v2.0.0" while the pin sits in an extra, or "no runtime dependencies" while a module that needs an extra
    is imported. They are not contradictions (`check_tree_claims` leaves them out); a reader is told why they hold.
    """
    return _tree_claims(root, readme)[1]
