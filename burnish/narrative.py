"""Architectural narrative extracted from the tree itself.

The README is a compilation of this narrative. Inventing a polished story
from the outside is a defect. This module only reports what the files
declare: module docstrings, pyproject scripts, CNS mentions and what a README
claims. It counts no tests: counting is Ghost Tools' job and running them
is Warden's, and the Finisher is handed both results.
"""

from __future__ import annotations

import ast
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .files import find_readme, python_files
from .marked import without_block


_UNPARSEABLE = (SyntaxError, ValueError, RecursionError, MemoryError)
_CNS = re.compile(r"\b(?:from cns|import cns|cns\.gate|cns\.graph)\b")


@dataclass
class ModuleStory:
    """What one Python module says about itself: its purpose, classes and functions."""

    path: str
    purpose: str
    classes: tuple[str, ...]
    functions: tuple[str, ...]
    cns_import: bool


@dataclass
class Narrative:
    """What a whole tree declares about itself, with nothing added from outside."""

    root: str
    name: str
    version: Optional[str]
    description: Optional[str]
    scripts: tuple[tuple[str, str], ...]
    modules: tuple[ModuleStory, ...]
    readme_exists: bool
    readme_text: str
    cns_mentioned: bool
    owns: tuple[str, ...]
    does_not_own: tuple[str, ...]
    unknowns: tuple[str, ...]
    claims_in_readme: tuple[str, ...]


def inspect_tree(root: Path) -> Narrative:
    """Read a tree and report only what its own files declare."""
    root = Path(root).resolve()
    name, version, description, scripts = _project_metadata(root)
    scan = _scan_python(root)
    readme = find_readme(root)
    readme_text = analysis_text(readme.read_text(encoding="utf-8", errors="replace")) if readme else ""
    return Narrative(
        root=str(root),
        name=name,
        version=version,
        description=description,
        scripts=scripts,
        modules=tuple(scan.modules),
        readme_exists=bool(readme),
        readme_text=readme_text,
        cns_mentioned=scan.cns_mentioned or bool(_CNS.search(readme_text)),
        owns=tuple(scan.owns),
        does_not_own=tuple(scan.does_not_own),
        unknowns=tuple(scan.unknowns),
        claims_in_readme=_readme_claims(readme_text),
    )


def analysis_text(text: str) -> str:
    """A README as the critic should read it: LF line ends, no BOM, Burnish's own generated block removed, one final newline."""
    text = without_block(text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n"))
    return text.rstrip() + "\n" if text.strip() else ""


def _project_metadata(root: Path) -> tuple[str, Optional[str], Optional[str], tuple[tuple[str, str], ...]]:
    """Name, version, description and console scripts, as pyproject.toml declares them.

    The name, version and description come from the `[project]` (or `[tool.poetry]`) table, and console scripts
    only from `[project.scripts]` or `[tool.poetry.scripts]`. A line such as `key = "a:b"` in any other
    table is a setting, not a command.
    """
    name, version, description = root.name, None, None
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return name, version, description, ()
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    tables = _tables(text)
    for table in ("project", "tool.poetry"):
        fields = tables.get(table, {})
        if isinstance(fields.get("name"), str):
            name = fields["name"]
            version = fields["version"] if isinstance(fields.get("version"), str) else None
            description = fields["description"] if isinstance(fields.get("description"), str) else None
            break
    scripts = tuple((key, value) for table in ("project.scripts", "tool.poetry.scripts")
                    for key, value in tables.get(table, {}).items() if isinstance(value, str) and ":" in value)
    return name, version, description, scripts


def _tables(text: str) -> dict[str, dict]:
    """The `project` and `tool.poetry` tables and their `scripts` tables, parsed, or read line by line if the TOML is broken."""
    wanted = {"project", "project.scripts", "tool.poetry", "tool.poetry.scripts"}
    try:
        data = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, ValueError):
        data = None
    if isinstance(data, dict):
        project = data.get("project") if isinstance(data.get("project"), dict) else {}
        tool = data.get("tool") if isinstance(data.get("tool"), dict) else {}
        poetry = tool.get("poetry")
        poetry = poetry if isinstance(poetry, dict) else {}
        found = {"project": project, "tool.poetry": poetry,
                 "project.scripts": project.get("scripts") if isinstance(project.get("scripts"), dict) else {},
                 "tool.poetry.scripts": poetry.get("scripts") if isinstance(poetry.get("scripts"), dict) else {}}
        return found
    out: dict[str, dict] = {}
    current = ""
    for line in text.splitlines():
        header = re.match(r"^\s*\[([^\[\]]+)\]\s*(?:#.*)?$", line)
        if header:
            current = header.group(1).strip()
            continue
        pair = re.match(r'^\s*([A-Za-z0-9_.-]+)\s*=\s*"([^"]*)"', line)
        if pair and current in wanted:
            out.setdefault(current, {})[pair.group(1)] = pair.group(2)
    return out


@dataclass
class _PythonScan:
    """What reading every Python file in a tree turned up."""

    modules: list[ModuleStory] = field(default_factory=list)
    cns_mentioned: bool = False
    owns: list[str] = field(default_factory=list)
    does_not_own: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


def _scan_python(root: Path) -> _PythonScan:
    """Read each Python file once; a file that cannot be read is listed as unknown, not skipped."""
    scan = _PythonScan()
    for path in python_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            scan.unknowns.append(rel)
            continue
        _record_module(scan, path, rel, src)
    return scan


def _record_module(scan: _PythonScan, path: Path, rel: str, src: str) -> None:
    """Add one module's story and ownership statements to the scan."""
    mentions_cns = bool(_CNS.search(src))
    scan.cns_mentioned = scan.cns_mentioned or mentions_cns
    classes, functions = _names(src)
    scan.modules.append(ModuleStory(path=rel, purpose=_module_purpose(src), classes=classes,
                                    functions=functions, cns_import=mentions_cns))
    for line in src.splitlines()[:80]:
        upper = line.strip().upper()
        if upper.startswith(("WHAT THIS OWNS", "WHAT IT OWNS")):
            scan.owns.append(rel)
        if "DOES NOT OWN" in upper:
            scan.does_not_own.append(rel)


def _readme_claims(readme_text: str, limit: int = 40) -> tuple[str, ...]:
    """The bullet and heading lines of a README: what it claims, before anyone checks."""
    lines = (line.strip() for line in readme_text.splitlines())
    return tuple(line for line in lines if line.startswith(("- ", "* ", "## ")))[:limit]


def _module_purpose(src: str) -> str:
    try:
        tree = ast.parse(src)
    except _UNPARSEABLE:
        return "(unparseable)"
    doc = ast.get_docstring(tree) or ""
    first = doc.strip().split("\n\n", 1)[0].strip().replace("\n", " ")
    return first[:400]


def _names(src: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        tree = ast.parse(src)
    except _UNPARSEABLE:
        return (), ()
    classes = tuple(
        n.name for n in tree.body if isinstance(n, ast.ClassDef)
    )
    functions = tuple(
        n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return classes, functions
