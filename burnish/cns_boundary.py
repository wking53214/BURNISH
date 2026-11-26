"""CNS interoperability analysis.

CNS is permanently read-only. This module never writes into a CNS tree,
never vendors CNS source, and never copies gate.py.

It records a *recommendation* for another repository:

    INTERNAL_CONVERGENCE | ADAPTER | NO_ACTION | DEFER

A CNS mention in a file is not a seam. A variable named subject_digest
is not proof that subject-binding semantics match CNS.

Digest interoperability: native digest and CNS digest are recorded
separately. Equality is never assumed.

Outcome translation: PASS / RETRY / TERMINAL_BREACH are CNS semantics.
This module will not map a domain status onto them without an explicit
Translation record.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .drift import _dependency_name, _dependency_strings, _optional_strings, _project
from .files import python_files
from .narrative import _CNS, Narrative, inspect_tree
from .provenance import Basis, Provenance, Source


class CnsRecommendation(str, Enum):
    """What to do about a repository's seam with CNS. Never includes modifying CNS."""

    INTERNAL_CONVERGENCE = "internal_convergence"
    ADAPTER = "adapter"
    NO_ACTION = "no_action"
    DEFER = "defer"


@dataclass(frozen=True)
class Translation:
    """One outcome as the source names it and as CNS would, with what the translation keeps and loses."""

    source_outcome: str
    source_semantics: str
    cns_outcome: str
    reason: str
    information_preserved: str
    information_lost: str
    authority_preserved: str
    epistemic_preserved: str
    subject_preserved: str
    provenance_preserved: str


@dataclass(frozen=True)
class CnsAnalysis:
    """A recommendation about a repository's CNS seam, the reasoning behind it, and the evidence it rests on."""

    repository: str
    recommendation: CnsRecommendation
    reason: str
    native_representation: str
    cns_representation: str
    meaning_preserved: str
    meaning_transformed: str
    meaning_collapsed: str
    meaning_dropped: str
    subject_binding: str
    digest_model: str
    translations: tuple[Translation, ...]
    cns_modified: str  # always "NO" for this campaign
    #: The evidence the recommendation required, what was found, and what was not read (item 17 of the plan).
    provenance: Provenance | None = None
    #: What evidence would change the recommendation.
    would_change: str = ""


@dataclass
class _Evidence:
    """What a tree shows about CNS, each piece with its place. Only real imports and declarations decide anything."""

    identity: Source | None = None              # the tree is CNS itself
    runtime_imports: list[Source] = field(default_factory=list)
    optional_imports: list[Source] = field(default_factory=list)   # behind a try that catches ImportError
    test_imports: list[Source] = field(default_factory=list)
    declared: list[Source] = field(default_factory=list)            # a runtime dependency on cns
    declared_optional: list[Source] = field(default_factory=list)   # an extra or a group
    mentions: list[Source] = field(default_factory=list)            # text that names CNS but imports nothing
    unread: list[str] = field(default_factory=list)


METHOD = ("read pyproject.toml for the project's name and its dependencies; parse every Python file and record each "
          "`import cns` or `from cns` statement and each `importlib.import_module(\"cns...\")`, keeping apart test "
          "files and imports that are optional (behind a `try` that catches ImportError, or run only when called); "
          "search the README and the Python text for other mentions of CNS, which are listed and decide nothing. "
          "The folder's name is not read.")
LOOKED_FOR = "a runtime import of cns, a dependency on cns in pyproject.toml, or a project named cns"
NOT_INSPECTED = ("whether the imported CNS names are used the way CNS defines them",
                 "what each adapter keeps and loses in translation",
                 "files Burnish skips: vendored, generated and fixture folders, and links")


def _is_test_file(relative: str) -> bool:
    """A file under a tests folder (any case) or named like a pytest file: its imports show what the tests use."""
    parts = relative.split("/")
    name = parts[-1]
    return any(p.lower() in {"tests", "test"} for p in parts[:-1]) or name.startswith("test_") \
        or name.endswith("_test.py") or name == "conftest.py"


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    names = []
    if isinstance(handler.type, ast.Tuple):
        names = [e for e in handler.type.elts]
    elif handler.type is not None:
        names = [handler.type]
    return handler.type is None or any(isinstance(n, ast.Name) and n.id in {"ImportError", "ModuleNotFoundError",
                                                                          "Exception"} for n in names)


def _cns_imports(tree: ast.AST) -> list[tuple[int, bool]]:
    """(line, guarded) for each import of the top-level `cns` package. Guarded: inside a `try` that catches ImportError."""
    guarded_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(_catches_import_error(h) for h in node.handlers):
            for inner in node.body:
                for sub in ast.walk(inner):
                    guarded_lines.add(getattr(sub, "lineno", 0))
    found = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        if any(n == "cns" or n.startswith("cns.") for n in names):
            line = getattr(node, "lineno", 0)
            found.append((line, line in guarded_lines))
        elif isinstance(node, ast.Call) and _imports_cns_when_called(node):
            found.append((node.lineno, True))   # loaded only when the call runs, so optional like a guarded import
    return sorted(found)


def _imports_cns_when_called(node: ast.AST) -> bool:
    """`importlib.import_module("cns.gate")` or `__import__("cns")`: an import of cns that runs when it is called."""
    if not isinstance(node, ast.Call) or not node.args:
        return False
    func = node.func
    called = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
    first = node.args[0]
    return called in {"import_module", "__import__"} and isinstance(first, ast.Constant) \
        and isinstance(first.value, str) and (first.value == "cns" or first.value.startswith("cns."))


def _identity(root: Path, data: dict | None) -> Source | None:
    """The tree is CNS itself when pyproject.toml names the project cns, or, with no project name, it ships the package."""
    project = data.get("project") if data else None
    name = project.get("name") if isinstance(project, dict) else None
    if isinstance(name, str):
        return Source("pyproject.toml", 0, f'project name "{name}"') if _dependency_name(name) == "cns" else None
    for package in ("cns/__init__.py", "src/cns/__init__.py"):
        if (root / package).is_file():
            return Source(package, 0, "the cns package itself, and no project name in pyproject.toml")
    return None


def _line_in(text: str, needle: str) -> int:
    at = text.find(needle)
    return text.count("\n", 0, at) + 1 if at >= 0 else 0


def _evidence(root: Path, nar: Narrative) -> _Evidence:
    ev = _Evidence()
    loaded = _project(root)
    data, raw = (loaded if loaded else (None, ""))
    ev.identity = _identity(root, data)
    if data:
        for spec in _dependency_strings(data):
            if _dependency_name(spec) == "cns":
                ev.declared.append(Source("pyproject.toml", _line_in(raw, spec), f"dependency {spec}"))
        for group, spec in _optional_strings(data):
            if _dependency_name(spec) == "cns":
                ev.declared_optional.append(Source("pyproject.toml", _line_in(raw, spec), f"{group}: {spec}"))
    for path in python_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (OSError, ValueError, SyntaxError):
            ev.unread.append(rel)
            continue
        imports = _cns_imports(tree)
        for line, guarded in imports:
            where = Source(rel, line, "import of cns" + (", optional (guarded, or run only when called)" if guarded else ""))
            if _is_test_file(rel):
                ev.test_imports.append(where)
            elif guarded:
                ev.optional_imports.append(where)
            else:
                ev.runtime_imports.append(where)
        if not imports:
            mention = _CNS.search(src)
            if mention:
                ev.mentions.append(Source(rel, src.count("\n", 0, mention.start()) + 1,
                                          f'mentions "{mention.group(0)}" in text, imports nothing'))
    mention = _CNS.search(nar.readme_text or "")
    if mention:
        ev.mentions.append(Source("README.md", nar.readme_text.count("\n", 0, mention.start()) + 1,
                                  f'mentions "{mention.group(0)}"'))
    return ev


def _decide(ev: _Evidence) -> tuple[CnsRecommendation, str, str, Basis, tuple[Source, ...]]:
    """(recommendation, reason, what would change it, basis, the evidence it rests on). The decision table of item 16."""
    uses = ev.runtime_imports + ev.optional_imports
    declares = ev.declared + ev.declared_optional
    if ev.identity is not None:
        return (CnsRecommendation.NO_ACTION,
                "This tree is CNS itself. CNS is the contract; Burnish does not modify it.",
                "Nothing: CNS is never a target.", "direct", (ev.identity,))
    if not uses and not declares:
        seen = " It mentions CNS or imports it in tests only, which decides nothing." \
            if ev.mentions or ev.test_imports else ""
        return (CnsRecommendation.NO_ACTION,
                "No code outside the tests imports cns and pyproject.toml does not depend on it, so there is no seam. "
                "Forcing one would be decorative." + seen,
                "A runtime import of cns together with a dependency on it in pyproject.toml.", "direct",
                tuple(ev.mentions + ev.test_imports))
    if uses and not declares:
        return (CnsRecommendation.DEFER,
                "Code imports cns but pyproject.toml does not depend on it, so the seam cannot be relied on. Declare the "
                "dependency, or remove the import, before deciding on an adapter.",
                "A dependency on cns in pyproject.toml (then: adapter), or no import of cns outside the tests "
                "(then: no action).", "direct", tuple(uses))
    if declares and not uses:
        return (CnsRecommendation.DEFER,
                "pyproject.toml depends on cns but no code outside the tests imports it, so it is not known what the "
                "seam is for. Use it or drop the dependency before deciding.",
                "A runtime import of cns (then: adapter), or no dependency on it (then: no action).", "direct",
                tuple(declares + ev.test_imports))
    return (CnsRecommendation.ADAPTER,
            "Code imports cns and pyproject.toml depends on it. Domain machinery stays here and a boundary adapter "
            "translates at the seam. Internal convergence is never recommended from these readings alone: it needs "
            "evidence that the repository's authoritative records already are CNS rows, which Burnish does not read.",
            "Evidence that the authoritative records already are CNS rows (a person's reading, then possibly internal "
            "convergence), or the import and the dependency both removed (then: no action).", "direct",
            tuple(uses + declares))


def analyse(root: Path, narrative: Narrative | None = None) -> CnsAnalysis:
    """Read a tree and recommend what to do about its CNS seam. Reads only; `cns_modified` is always NO.

    The decision rests on evidence alone (item 16 of the remediation plan): whether the tree is CNS by its project name,
    whether code outside the tests imports cns, and whether pyproject.toml depends on it. A mention in text, an import in
    a test and the folder's name decide nothing. Every recommendation carries its evidence (item 17).
    """
    root = Path(root)
    nar = narrative or inspect_tree(root)
    ev = _evidence(root, nar)
    rec, reason, would_change, basis, evidence = _decide(ev)
    project = nar.name if nar.name and nar.name != "(unnamed)" else Path(nar.root).name
    provenance = Provenance(
        claim=f"what to do about {project}'s seam with CNS: {rec.value}",
        claim_at=Source(what="this tree's imports and pyproject.toml"),
        evidence=evidence, method=METHOD, basis=basis,
        not_inspected=NOT_INSPECTED + tuple(f"{p} (did not parse)" for p in ev.unread),
        reason=reason)
    importing = sorted({s.path for s in ev.runtime_imports + ev.optional_imports})
    is_cns = rec is CnsRecommendation.NO_ACTION and ev.identity is not None
    return CnsAnalysis(
        repository=project,
        recommendation=rec,
        reason=reason,
        native_representation=("cns (the contract itself)" if is_cns else
                               ("see importing modules: " + ", ".join(importing)) if importing else
                               "domain-owned" if rec is CnsRecommendation.NO_ACTION else "UNKNOWN"),
        cns_representation="self" if is_cns else ("optional import of cns, not vendored" if importing else "none"),
        meaning_preserved="n/a" if rec is CnsRecommendation.NO_ACTION else "UNKNOWN without reading each adapter",
        meaning_transformed="none" if rec is CnsRecommendation.NO_ACTION else "UNKNOWN",
        meaning_collapsed="none" if rec is CnsRecommendation.NO_ACTION else "UNKNOWN",
        meaning_dropped="none" if rec is CnsRecommendation.NO_ACTION else "UNKNOWN",
        subject_binding=("CNS owns subject_digest; this campaign does not reimplement it" if is_cns else
                         "do not treat a field named subject_digest as proof of CNS binding"),
        digest_model=("native CNS canonicalization; not copied here" if is_cns else
                      "record native digest and CNS digest separately; never silently replace"),
        translations=(),
        cns_modified="NO",
        provenance=provenance,
        would_change=would_change,
    )


def to_dict(a: CnsAnalysis) -> dict:
    """The analysis as JSON-ready data, evidence and provenance included."""
    return {
        "repository": a.repository,
        "recommendation": a.recommendation.value,
        "reason": a.reason,
        "native_representation": a.native_representation,
        "cns_representation": a.cns_representation,
        "meaning_preserved": a.meaning_preserved,
        "meaning_transformed": a.meaning_transformed,
        "meaning_collapsed": a.meaning_collapsed,
        "meaning_dropped": a.meaning_dropped,
        "subject_binding": a.subject_binding,
        "digest_model": a.digest_model,
        "cns_modified": a.cns_modified,
        "would_change": a.would_change,
        "evidence": [src.render() for src in a.provenance.evidence] if a.provenance else [],
        "provenance": a.provenance.lines() if a.provenance else [],
        "translations": [
            {
                "source_outcome": t.source_outcome,
                "cns_outcome": t.cns_outcome,
                "reason": t.reason,
            }
            for t in a.translations
        ],
    }
