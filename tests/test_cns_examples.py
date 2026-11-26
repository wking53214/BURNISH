"""Item 18 of the remediation plan: the CNS analyser against example trees whose right answer is known.

Each example is a small tree written into a scratch folder, with the recommendation a reader would give from its imports
and its pyproject.toml. The analyser must give that answer, give it whatever the folder is called, never recommend
internal convergence on its own, carry the evidence it rests on, and write nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from burnish.cns_boundary import CnsRecommendation, analyse, to_dict

PROJECT = '[project]\nname = "{name}"\nversion = "0.1.0"\ndependencies = [{deps}]\n{extra}'
CNS_DEP = '"cns @ git+https://github.com/wking53214/CNS.git@v4.1.0"'
MODULE = '"""Demo."""\n'

EXAMPLES: dict[str, tuple[dict[str, str], CnsRecommendation]] = {
    "cns itself, named by pyproject.toml": (
        {"pyproject.toml": PROJECT.format(name="cns", deps="", extra=""), "cns/__init__.py": MODULE,
         "cns/gate.py": MODULE + "from cns import seat\n"}, CnsRecommendation.NO_ACTION),
    "cns itself, with no pyproject.toml": (
        {"cns/__init__.py": MODULE, "cns/gate.py": MODULE}, CnsRecommendation.NO_ACTION),
    "a mention in the README only": (
        {"pyproject.toml": PROJECT.format(name="demo", deps="", extra=""),
         "README.md": "# demo\n\nOld notes said `from cns import gate`.\n",
         "demo/__init__.py": MODULE}, CnsRecommendation.NO_ACTION),
    "a mention in a comment and a string only": (
        {"pyproject.toml": PROJECT.format(name="demo", deps="", extra=""),
         "demo/__init__.py": MODULE + "# we used to do: from cns import gate\nHELP = 'import cns is not needed'\n"},
        CnsRecommendation.NO_ACTION),
    "an import in the tests only": (
        {"pyproject.toml": PROJECT.format(name="demo", deps="", extra=""), "demo/__init__.py": MODULE,
         "tests/test_seam.py": "from cns import gate\n"}, CnsRecommendation.NO_ACTION),
    "a runtime import and a runtime dependency": (
        {"pyproject.toml": PROJECT.format(name="demo", deps=CNS_DEP, extra=""),
         "demo/seam.py": MODULE + "from cns.gate import GateOutcome\n"}, CnsRecommendation.ADAPTER),
    "a guarded import and an extra": (
        {"pyproject.toml": PROJECT.format(name="demo", deps="", extra=f"\n[project.optional-dependencies]\ncns = [{CNS_DEP}]\n"),
         "demo/seam.py": MODULE + "try:\n    import cns\nexcept ImportError:\n    cns = None\n"},
        CnsRecommendation.ADAPTER),
    "an import run only when called, and an extra": (
        {"pyproject.toml": PROJECT.format(name="demo", deps="", extra=f"\n[project.optional-dependencies]\ncns = [{CNS_DEP}]\n"),
         "demo/seam.py": MODULE + "import importlib\n\n\ndef gate():\n    return importlib.import_module('cns.gate')\n"},
        CnsRecommendation.ADAPTER),
    "a runtime import with no dependency declared": (
        {"pyproject.toml": PROJECT.format(name="demo", deps="", extra=""),
         "demo/seam.py": MODULE + "import cns.graph\n"}, CnsRecommendation.DEFER),
    "a dependency declared with no import": (
        {"pyproject.toml": PROJECT.format(name="demo", deps=CNS_DEP, extra=""), "demo/__init__.py": MODULE},
        CnsRecommendation.DEFER),
    "nothing about cns at all": (
        {"pyproject.toml": PROJECT.format(name="demo", deps='"click>=8"', extra=""), "demo/__init__.py": MODULE + "import click\n"},
        CnsRecommendation.NO_ACTION),
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("folder", ["demo", "CNS", "composition-engine", "a-copy"])
@pytest.mark.parametrize("example", list(EXAMPLES), ids=list(EXAMPLES))
def test_each_example_gets_its_known_answer_whatever_the_folder_is_called(example: str, folder: str, tmp_path: Path):
    files, expected = EXAMPLES[example]
    root = tmp_path / folder
    _write(root, files)
    before = _snapshot(root)
    a = analyse(root)
    assert a.recommendation is expected, f"{example} in {folder}/: {a.reason}"
    assert a.recommendation is not CnsRecommendation.INTERNAL_CONVERGENCE
    assert a.cns_modified == "NO" and _snapshot(root) == before


@pytest.mark.parametrize("example", list(EXAMPLES), ids=list(EXAMPLES))
def test_each_recommendation_lists_the_evidence_it_required(example: str, tmp_path: Path):
    """Item 17: the evidence, the method, what was not read, and what would change the answer."""
    files, expected = EXAMPLES[example]
    _write(tmp_path, files)
    a = analyse(tmp_path)
    assert a.provenance is not None and a.would_change
    assert a.provenance.method and a.provenance.not_inspected and a.provenance.reason == a.reason
    if expected is not CnsRecommendation.NO_ACTION or example.startswith(("cns itself", "a mention", "an import in")):
        assert a.provenance.evidence, f"{example}: a recommendation with no evidence listed"
    for source in a.provenance.evidence:
        assert source.path in files, f"{example}: evidence points at {source.path}, which is not in the tree"
    out = to_dict(a)
    assert out["evidence"] == [s.render() for s in a.provenance.evidence] and len(out["provenance"]) == 6
