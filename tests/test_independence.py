"""Burnish imports Warden's shapes and no other role; it writes and counts nothing."""

import ast
from pathlib import Path

import burnish

ROOT = Path(burnish.__file__).parent
_OTHER_ROLES = {"drafter", "ghost_buster", "swizzle", "assay"}


def _imports(module: str) -> set[str]:
    tree = ast.parse((ROOT / f"{module}.py").read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_the_readme_critic_stands_alone():
    internal = {name for name in _imports("readme_critic") if name.startswith(".")}
    assert internal == set()


def test_no_module_imports_another_role():
    offenders = {p.name: sorted(n for n in _imports(p.stem) if n.split(".")[0] in _OTHER_ROLES)
                 for p in ROOT.glob("*.py")}
    assert {k: v for k, v in offenders.items() if v} == {}


def test_no_burnish_module_opens_a_file_for_writing():
    """Writing a repository is Warden's job, behind a human grant."""
    offenders = []
    for path in ROOT.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr in {"write_text", "write_bytes", "unlink", "rmtree"}:
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


def test_the_duplicated_roles_are_gone():
    """Proposing moved to Drafter; the documentation-honesty oracle counted what Ghost counts."""
    assert {"drafters.py", "oracle.py", "craft.py"}.isdisjoint({p.name for p in ROOT.glob("*.py")})


def test_no_burnish_module_counts_tests():
    source = "\n".join(p.read_text(encoding="utf-8") for p in ROOT.glob("*.py"))
    assert "test_functions" not in source and "test_count_claims" not in source
