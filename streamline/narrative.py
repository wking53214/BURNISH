"""Architectural narrative extracted from the tree itself.

The README is a compilation of this narrative. Inventing a polished story
from the outside is a defect. This module only reports what the files
declare: module docstrings, pyproject scripts, test function counts,
CNS mentions, and whether a README already claims more than the tree
can support.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_TEST_FN = re.compile(r"^test_", re.M)
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
    test_functions: int
    test_files: tuple[str, ...]
    readme_exists: bool
    readme_text: str
    cns_mentioned: bool
    owns: tuple[str, ...]
    does_not_own: tuple[str, ...]
    unknowns: tuple[str, ...]
    claims_in_readme: tuple[str, ...]

    def test_count_claims(self) -> tuple[tuple[str, int], ...]:
        """Integers that a README/PROVENANCE presents as a test count."""
        text = self.readme_text
        found = []
        for m in re.finditer(
            r"(\d+)\s+tests?\s+(?:passed|pass|exist|in the|in this)",
            text,
            re.I,
        ):
            found.append((m.group(0), int(m.group(1))))
        for m in re.finditer(r"claims?\s+(\d+)\s+test", text, re.I):
            found.append((m.group(0), int(m.group(1))))
        return tuple(found)


def inspect_tree(root: Path) -> Narrative:
    """Read a tree and report only what its own files declare."""
    root = Path(root).resolve()
    name, version, description, scripts = _project_metadata(root)
    scan = _scan_python(root)
    readme = _first_readme(root)
    readme_text = readme.read_text(encoding="utf-8", errors="replace") if readme else ""
    return Narrative(
        root=str(root),
        name=name,
        version=version,
        description=description,
        scripts=scripts,
        modules=tuple(scan.modules),
        test_functions=scan.test_functions,
        test_files=tuple(scan.test_files),
        readme_exists=bool(readme),
        readme_text=readme_text,
        cns_mentioned=scan.cns_mentioned or bool(_CNS.search(readme_text)),
        owns=tuple(scan.owns),
        does_not_own=tuple(scan.does_not_own),
        unknowns=tuple(scan.unknowns),
        claims_in_readme=_readme_claims(readme_text),
    )


def _project_metadata(root: Path) -> tuple[str, Optional[str], Optional[str], tuple[tuple[str, str], ...]]:
    """Name, version, description and console scripts, as pyproject.toml declares them."""
    name, version, description = root.name, None, None
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return name, version, description, ()
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    declared = {key: re.search(rf'^{key}\s*=\s*"([^"]+)"', text, re.M) for key in ("version", "description", "name")}
    version = declared["version"].group(1) if declared["version"] else None
    description = declared["description"].group(1) if declared["description"] else None
    name = declared["name"].group(1) if declared["name"] else name
    scripts = tuple((m.group(1), m.group(2))
                    for m in re.finditer(r'^([A-Za-z0-9_-]+)\s*=\s*"([^"]+:[^"]+)"', text, re.M))
    return name, version, description, scripts


@dataclass
class _PythonScan:
    """What reading every Python file in a tree turned up."""

    modules: list[ModuleStory] = field(default_factory=list)
    test_functions: int = 0
    test_files: list[str] = field(default_factory=list)
    cns_mentioned: bool = False
    owns: list[str] = field(default_factory=list)
    does_not_own: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


def _scan_python(root: Path) -> _PythonScan:
    """Read each Python file once; a file that cannot be read is listed as unknown, not skipped."""
    scan = _PythonScan()
    files = [p for p in root.rglob("*.py") if ".git" not in p.parts and "site-packages" not in p.parts]
    for path in sorted(files):
        rel = path.relative_to(root).as_posix()
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            scan.unknowns.append(rel)
            continue
        _record_module(scan, path, rel, src)
    return scan


def _record_module(scan: _PythonScan, path: Path, rel: str, src: str) -> None:
    """Add one module's story, test count and ownership statements to the scan."""
    mentions_cns = bool(_CNS.search(src))
    scan.cns_mentioned = scan.cns_mentioned or mentions_cns
    classes, functions = _names(src)
    if _is_test_path(path, rel):
        count = _count_test_functions(src)
        if count:
            scan.test_functions += count
            scan.test_files.append(rel)
    scan.modules.append(ModuleStory(path=rel, purpose=_module_purpose(src), classes=classes,
                                    functions=functions, cns_import=mentions_cns))
    for line in src.splitlines()[:80]:
        upper = line.strip().upper()
        if upper.startswith(("WHAT THIS OWNS", "WHAT IT OWNS")):
            scan.owns.append(rel)
        if "DOES NOT OWN" in upper:
            scan.does_not_own.append(rel)


def _is_test_path(path: Path, rel: str) -> bool:
    return "test" in path.name.lower() or "/tests/" in f"/{rel.lower()}/"


def _readme_claims(readme_text: str, limit: int = 40) -> tuple[str, ...]:
    """The bullet and heading lines of a README: what it claims, before anyone checks."""
    lines = (line.strip() for line in readme_text.splitlines())
    return tuple(line for line in lines if line.startswith(("- ", "* ", "## ")))[:limit]


def _first_readme(root: Path) -> Optional[Path]:
    for name in ("README.md", "Readme.md", "readme.md"):
        p = root / name
        if p.is_file():
            return p
    return None


def _module_purpose(src: str) -> str:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return "(unparseable)"
    doc = ast.get_docstring(tree) or ""
    first = doc.strip().split("\n\n", 1)[0].strip().replace("\n", " ")
    return first[:400]


def _names(src: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return (), ()
    classes = tuple(
        n.name for n in tree.body if isinstance(n, ast.ClassDef)
    )
    functions = tuple(
        n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return classes, functions


def _count_test_functions(src: str) -> int:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return len(_TEST_FN.findall(src))
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            n += 1
    return n
