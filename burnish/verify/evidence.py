"""Comparison input: what the tree says about which packages its program loads, and how.

It reads `pyproject.toml` (the runtime and optional dependencies, and the entry points in `[project.scripts]`) and the
imports of the project's own modules, and follows them from the entry points the way Python would when the program
starts. Every route from an entry point to a package is one of three kinds:

  * load: every import on the way runs when the program starts,
  * guarded: an import on the way sits behind a `try` that expects the import to fail, or under `TYPE_CHECKING`, so the
    program is written to go on without it,
  * deferred: an import on the way sits inside a function with no such guard; whether the function runs on every use
    cannot be told from here.

A deferred step stays deferred whatever comes after it, so a reading never makes a route look safer than it is.

The reading is complete only when every module on a route was parsed and no module on a route imports by name
(`importlib.import_module`, `__import__`). An incomplete reading never contradicts a claim.

WHAT IT DOES NOT OWN
    Running the program. Everything here is read from files; a module loaded by a plugin system, a subprocess or a path
    built at run time is not seen, which is why a reading lists what it could not inspect.
"""

from __future__ import annotations

import ast
import heapq
import re
import sys
import tomllib
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Optional

from ..files import is_protected, python_files
from ..provenance import Source

__all__ = ["Route", "Reading", "read_tree"]

_RANK = {"load": 0, "guarded": 1, "deferred": 2}
_EXPECTS_IT_MAY_FAIL = frozenset({"ImportError", "ModuleNotFoundError", "Exception", "BaseException"})


@dataclass(frozen=True)
class Route:
    """How a package is reached from an entry point: its kind, and the import that reaches it."""

    kind: str          # "load", "guarded" or "deferred"
    at: Source         # the import statement that names the package
    entry: str         # the entry module the route starts from


@dataclass
class Reading:
    """What the tree declares and what its program loads."""

    runtime: dict[str, int] = field(default_factory=dict)              # distribution -> pyproject.toml line
    optional: dict[str, tuple[str, int]] = field(default_factory=dict)  # distribution -> (extra or group, line)
    entries: list[tuple[str, Source]] = field(default_factory=list)     # entry module, where it is declared
    names: dict[str, str] = field(default_factory=dict)                 # a word that names a package -> its module
    routes: dict[str, list[Route]] = field(default_factory=dict)        # module -> how it is reached
    unread: list[str] = field(default_factory=list)                     # modules on a route that did not parse
    dynamic: list[Source] = field(default_factory=list)                 # imports by name on a route
    readable: bool = True                                               # False: no pyproject.toml could be read

    def complete(self) -> bool:
        return self.readable and bool(self.entries) and not self.unread and not self.dynamic

    def declared(self, module: str) -> Optional[Source]:
        """Where pyproject.toml declares the distribution that provides `module`, or None."""
        for dist, line in self.runtime.items():
            if module in _modules_of(dist):
                return Source("pyproject.toml", line, f"declares {dist} as a runtime dependency")
        for dist, (where, line) in self.optional.items():
            if module in _modules_of(dist):
                return Source("pyproject.toml", line, f"declares {dist} only as an optional dependency ({where})")
        return None


def _normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _modules_of(dist: str) -> set[str]:
    """The top-level modules a distribution provides: from installed metadata when it is installed, else its own name."""
    try:
        installed = metadata.packages_distributions()
    except (OSError, ValueError):
        installed = {}   # no metadata to read: the distribution's own name is all there is to go on
    return {dist.replace("-", "_")} | {module for module, owners in installed.items()
                                       if any(_normal(owner) == dist for owner in owners)}


def _line_of(text: str, needle: str) -> int:
    for number, line in enumerate(text.splitlines(), 1):
        if needle in line and not line.lstrip().startswith("#"):
            return number
    return 0


def _dist(spec: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", spec)
    return _normal(match.group(1)) if match else ""


def read_tree(root: Path, project: str = "") -> Reading:
    """Read the tree at `root`: its declarations, its entry points and every route from them to a package."""
    root = Path(root)
    reading = Reading()
    try:
        raw = (root / "pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(raw)
    except (OSError, ValueError):
        reading.readable = False
        return reading
    found = data.get("project")
    project_table: dict = found if isinstance(found, dict) else {}
    for spec in project_table.get("dependencies") or []:
        if isinstance(spec, str) and (name := _dist(spec)):
            reading.runtime[name] = _line_of(raw, spec)
    for where, specs in (project_table.get("optional-dependencies") or {}).items():
        for spec in specs if isinstance(specs, list) else []:
            if isinstance(spec, str) and (name := _dist(spec)) and name not in reading.runtime:
                reading.optional[name] = (f"extra {where}", _line_of(raw, spec))
    modules = _own_modules(root)
    for table in ("scripts", "gui-scripts"):
        for command, target in (project_table.get(table) or {}).items():
            if isinstance(target, str):
                module = target.split(":")[0].strip()
                if module in modules:
                    reading.entries.append((module, Source("pyproject.toml", _line_of(raw, target),
                                                           f"entry point {command} = {target}")))
    if not reading.entries:   # no entry point: importing the package is how the program starts
        for module, path in sorted(modules.items()):
            if "." not in module and path.name == "__init__.py":
                reading.entries.append((module, Source(path.relative_to(root).as_posix(), 0, f"the package {module}")))
    _follow(root, modules, reading)
    for dist in list(reading.runtime) + list(reading.optional):
        for module in _modules_of(dist):
            reading.names.setdefault(module.lower(), module)
        reading.names.setdefault(dist, dist.replace("-", "_"))
    for module in set(reading.routes) | _imported_anywhere(modules):
        reading.names.setdefault(module.lower(), module)
    reading.names.pop(project.lower(), None)
    return reading


def _imported_anywhere(modules: dict[str, Path]) -> set[str]:
    """Every third-party top-level module any of the project's own modules imports, reached or not."""
    out: set[str] = set()
    for module, path in modules.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError, RecursionError, MemoryError):
            continue
        out |= {edge.target for edge in _edges(tree, module, path.name == "__init__.py", modules)[0] if not edge.own}
    return out


def _own_modules(root: Path) -> dict[str, Path]:
    """Every module of the project's own packages, by dotted name, outside tests and protected files."""
    out: dict[str, Path] = {}
    for path in python_files(root):
        relative = path.relative_to(root)
        if is_protected(relative.as_posix()) or relative.parts[0] in ("tests", "test", "docs", "exemplars"):
            continue
        parts = list(relative.with_suffix("").parts)
        if parts[0] == "src":
            parts = parts[1:]
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            out[".".join(parts)] = path
    return out


@dataclass(frozen=True)
class _Edge:
    target: str      # an own module's dotted name, or a third-party top-level module
    how: str         # "load", "guarded" or "deferred"
    line: int
    own: bool


def _edges(tree: ast.AST, module: str, is_package: bool, modules: dict[str, Path]) -> tuple[list[_Edge], list[int]]:
    """The imports in one parsed module, and the lines of its imports by name."""
    package = module if is_package else module.rpartition(".")[0]
    edges: list[_Edge] = []
    dynamic: list[int] = []
    stack: list[tuple[ast.AST, bool, bool]] = [(tree, False, False)]
    while stack:
        node, in_function, in_guard = stack.pop()
        how = "guarded" if in_guard else "deferred" if in_function else "load"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for name in _imported_names(node, package):
                edges.extend(_resolve(name, how, node.lineno, modules))
            continue
        if isinstance(node, ast.Call) and _calls_import_by_name(node):
            dynamic.append(node.lineno)
        function = in_function or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        body_guard = in_guard or (isinstance(node, (ast.Try, ast.TryStar)) and any(map(_catches, node.handlers))) \
            or (isinstance(node, ast.If) and _is_type_checking(node.test))
        for name, value in ast.iter_fields(node):
            for child in value if isinstance(value, list) else [value]:
                if isinstance(child, ast.AST):
                    stack.append((child, function, body_guard if name == "body" else in_guard))
    return edges, dynamic


def _imported_names(node: ast.Import | ast.ImportFrom, package: str) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level:
        base = package.split(".") if package else []
        base = base[:len(base) - (node.level - 1)] if node.level > 1 else base
        stem = ".".join(base + ([node.module] if node.module else []))
    else:
        stem = node.module or ""
    return [stem] + [f"{stem}.{alias.name}" for alias in node.names]


def _resolve(name: str, how: str, line: int, modules: dict[str, Path]) -> list[_Edge]:
    """`name` as edges: an own module and the packages above it, or one third-party top-level module."""
    if not name:
        return []
    parts = name.split(".")
    own = [".".join(parts[:i]) for i in range(1, len(parts) + 1) if ".".join(parts[:i]) in modules]
    if own:
        return [_Edge(target, how, line, True) for target in own]
    top = parts[0]
    if top in sys.stdlib_module_names or top == "__future__" or top in {m.split(".")[0] for m in modules}:
        return []
    return [_Edge(top, how, line, False)]


def _calls_import_by_name(node: ast.Call) -> bool:
    func = node.func
    called = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
    return called in ("import_module", "__import__")


def _catches(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    named = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(isinstance(n, ast.Name) and n.id in _EXPECTS_IT_MAY_FAIL for n in named)


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def _follow(root: Path, modules: dict[str, Path], reading: Reading) -> None:
    """Walk from each entry point, keeping for each own module the safest-for-the-claim (lowest) kind it is reached by."""
    parsed: dict[str, Optional[tuple[list[_Edge], list[int]]]] = {}
    for entry, _ in reading.entries:
        best: dict[str, int] = {}
        queue = [(0, entry)]
        while queue:
            rank, module = heapq.heappop(queue)
            if best.get(module, 99) <= rank:
                continue
            best[module] = rank
            if module not in parsed:
                path = modules[module]
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
                    parsed[module] = _edges(tree, module, path.name == "__init__.py", modules)
                except (OSError, SyntaxError, ValueError, RecursionError, MemoryError):
                    parsed[module] = None
            found = parsed[module]
            relative = modules[module].relative_to(root).as_posix()
            if found is None:
                if relative not in reading.unread:
                    reading.unread.append(relative)
                continue
            edges, dynamic = found
            for line in dynamic:
                source = Source(relative, line, "imports a module by name")
                if source not in reading.dynamic:
                    reading.dynamic.append(source)
            for edge in edges:
                kind = max(rank, _RANK[edge.how])
                if edge.own:
                    heapq.heappush(queue, (kind, edge.target))
                else:
                    name = {v: k for k, v in _RANK.items()}[kind]
                    route = Route(name, Source(relative, edge.line, f"imports {edge.target}"
                                               + {"load": " when the program starts", "guarded": " behind a guard",
                                                  "deferred": " inside a function, unguarded"}[name]), entry)
                    if route not in reading.routes.setdefault(edge.target, []):
                        reading.routes[edge.target].append(route)
