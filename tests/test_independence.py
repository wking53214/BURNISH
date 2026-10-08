"""The reviewer and the oracle never import each other; Streamline writes nothing by itself."""

import ast
from pathlib import Path

import streamline

ROOT = Path(streamline.__file__).parent


def _imports(module: str) -> set[str]:
    tree = ast.parse((ROOT / f"{module}.py").read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_the_oracle_does_not_import_the_critic():
    assert ".critic" not in _imports("oracle")


def test_the_critic_does_not_import_the_oracle():
    assert ".oracle" not in _imports("critic")


def test_the_readme_critic_stands_alone():
    internal = {name for name in _imports("readme_critic") if name.startswith(".")}
    assert internal == set()


def test_no_streamline_module_opens_a_file_for_writing():
    """Writing a repository is Elegant's job, behind a human grant."""
    offenders = []
    for path in ROOT.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr in {"write_text", "write_bytes", "unlink", "rmtree"}:
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []
