"""Mechanical checks for Python: the criteria a program can judge without an opinion.

Each check reports what it saw and where, and names the criterion it enforces.
A check never rewrites anything and never scores anything. If a file cannot be
parsed, that is reported as a finding of its own: silence about a file that
could not be read would read as a clean file, and silence is the defect.

THE CHECKS

  PY-EXC       a bare `except:`
  PY-SWALLOW   a handler whose body is only `pass`
  PY-STAR      `from x import *`
  PY-DOC       a public module, class or function with no docstring
  PY-NAME      a function not in snake_case, or a class not in CapWords
  PY-CMP       `== None`, `== True`, `== False`
  PY-RET       a bare `return` in a function that returns a value elsewhere (write `return None`)
  PY-TYPE      a public function with an unannotated parameter or return

Test files are held to the checks about behavior (PY-EXC, PY-SWALLOW, PY-STAR,
PY-CMP, PY-RET). They are not asked for docstrings or annotations, because a
test's name is its documentation.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

__all__ = ["Finding", "CHECK_IDS", "check_source", "check_tree", "summarize", "only"]

CHECK_IDS = ("PY-EXC", "PY-SWALLOW", "PY-STAR", "PY-DOC", "PY-NAME", "PY-CMP", "PY-RET", "PY-TYPE")

_SKIPPED_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", ".pytest_cache", "target",
                 "node_modules", ".ruff_cache", ".mypy_cache"}
_SNAKE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_{0,2}$")
_CAPWORDS = re.compile(r"^_?[A-Z][A-Za-z0-9]*$")


@dataclass(frozen=True)
class Finding:
    """One thing a check found: which check, where, and what is wrong."""

    check: str
    path: str
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.check}: {self.message}"


def check_tree(root: Path) -> list[Finding]:
    """Every finding in every Python file under `root`, in path and line order."""
    root = Path(root)
    findings: list[Finding] = []
    for path in _python_files(root):
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(check_source(source, relative, is_test=_is_test_file(relative)))
    return sorted(findings, key=lambda f: (f.path, f.line, f.check))


def check_source(source: str, path: str, *, is_test: bool = False) -> list[Finding]:
    """Every finding in one file's source text."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [Finding("PY-PARSE", path, error.lineno or 1,
                        f"could not be parsed ({error.msg}); no other check can speak for this file")]
    found: list[Finding] = []
    found.extend(_handlers(tree, path))
    found.extend(_imports(tree, path))
    found.extend(_comparisons(tree, path))
    found.extend(_returns(tree, path))
    if not is_test:
        found.extend(_docstrings(tree, path))
        found.extend(_names(tree, path))
        found.extend(_annotations(tree, path))
    return found


def _python_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if not _SKIPPED_DIRS.intersection(path.relative_to(root).parts):
            yield path


def _is_test_file(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return relative.startswith("tests/") or name.startswith("test_") or name == "conftest.py"


def _functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _handlers(tree: ast.AST, path: str) -> Iterator[Finding]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            yield Finding("PY-EXC", path, node.lineno,
                          "bare `except:` catches everything, including KeyboardInterrupt; name the exceptions")
        if all(isinstance(statement, ast.Pass) for statement in node.body):
            yield Finding("PY-SWALLOW", path, node.lineno,
                          "the handler only passes, so a failure looks like success; handle it or let it rise")


def _imports(tree: ast.AST, path: str) -> Iterator[Finding]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            yield Finding("PY-STAR", path, node.lineno,
                          f"`from {node.module or '.'} import *` hides where names come from")


def _comparisons(tree: ast.AST, path: str) -> Iterator[Finding]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and _equates_a_singleton(node):
            yield Finding("PY-CMP", path, node.lineno,
                          "compare to None with `is` / `is not`, and do not compare a bool with `==`")


def _equates_a_singleton(comparison: ast.Compare) -> bool:
    left = comparison.left
    for operator, right in zip(comparison.ops, comparison.comparators):
        if isinstance(operator, (ast.Eq, ast.NotEq)) and (_is_singleton(left) or _is_singleton(right)):
            return True
        left = right
    return False


def _is_singleton(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and (node.value is None or isinstance(node.value, bool))


def _returns(tree: ast.AST, path: str) -> Iterator[Finding]:
    for function in _functions(tree):
        returns = [n for n in _own_nodes(function) if isinstance(n, ast.Return)]
        returns_a_value = any(r.value is not None for r in returns)
        bare_returns = [r for r in returns if r.value is None]
        if returns_a_value and bare_returns:
            yield Finding("PY-RET", path, bare_returns[0].lineno,
                          f"`{function.name}` has a bare `return` beside returns with a value; "
                          "write `return None` where None is meant (PEP 8)")


def _own_nodes(function: ast.AST) -> Iterator[ast.AST]:
    """The nodes in a function's own body, not those of functions nested inside it."""
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))


def _docstrings(tree: ast.Module, path: str) -> Iterator[Finding]:
    if ast.get_docstring(tree) is None and tree.body:
        yield Finding("PY-DOC", path, 1, "the module has no docstring")
    for node in _public_definitions(tree):
        if ast.get_docstring(node) is None and not _is_trivial_member(node):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            yield Finding("PY-DOC", path, node.lineno, f"public {kind} `{node.name}` has no docstring")


def _public_definitions(tree: ast.Module) -> Iterator[ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef]:
    """Public top-level definitions and the public methods of public classes."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
            yield node
        elif isinstance(node, ast.ClassDef) and _is_public(node.name):
            yield node
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(member.name):
                    yield member


def _is_trivial_member(node: ast.AST) -> bool:
    """A property, or a body of one short line, says everything its name does."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    decorated_as_property = any(isinstance(d, ast.Name) and d.id in {"property", "cached_property"}
                                for d in node.decorator_list)
    return decorated_as_property or len(node.body) == 1 and isinstance(node.body[0], (ast.Return, ast.Pass))


def _names(tree: ast.AST, path: str) -> Iterator[Finding]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _SNAKE.match(node.name):
            yield Finding("PY-NAME", path, node.lineno, f"function `{node.name}` is not lowercase_with_underscores")
        elif isinstance(node, ast.ClassDef) and not _CAPWORDS.match(node.name):
            yield Finding("PY-NAME", path, node.lineno, f"class `{node.name}` is not CapWords")


def _annotations(tree: ast.Module, path: str) -> Iterator[Finding]:
    for node in _public_definitions(tree):
        if isinstance(node, ast.ClassDef):
            continue
        missing = _unannotated(node)
        if missing:
            yield Finding("PY-TYPE", path, node.lineno,
                          f"`{node.name}` has no annotation for: {', '.join(missing)}")


def _unannotated(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    arguments = function.args
    every = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    if arguments.vararg:
        every.append(arguments.vararg)
    if arguments.kwarg:
        every.append(arguments.kwarg)
    missing = [a.arg for a in every if a.annotation is None and a.arg not in {"self", "cls"}]
    if function.returns is None and function.name != "__init__":
        missing.append("return")
    return missing


def summarize(findings: Sequence[Finding]) -> dict[str, int]:
    """How many findings each check produced, for the CLI's one-line summary."""
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.check] = counts.get(finding.check, 0) + 1
    return counts


def only(findings: Iterable[Finding], *checks: str) -> list[Finding]:
    """The findings produced by the named checks."""
    return [f for f in findings if f.check in checks]
