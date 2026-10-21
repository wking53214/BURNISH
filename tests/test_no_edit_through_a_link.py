"""The finisher never proposes a write whose path is a symbolic link, or lies under one: a write through a link lands
on its target, which may not exist yet or may be outside the folder being finished."""

from pathlib import Path

import pytest
from cns.seat import Facts, FileEdit

from burnish.finisher import Burnish

FACTS = Facts(suite=None, remaining=(), cycles=0)
MODULE = '"""A module."""\n\nVALUE = 1   \n'
KINDS = ["outside", "inside", "dangling"]


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    """A folder with real Python (so there is something to tidy) and a folder next to it that must stay untouched."""
    target, outside = tmp_path / "repo", tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    (target / "pkg").mkdir()
    (target / "pkg" / "__init__.py").write_text(MODULE, encoding="utf-8")
    (target / "docs").mkdir()
    (target / "docs" / "real.md").write_text("# real\n\nInside.\n", encoding="utf-8")
    (outside / "real.md").write_text("# outside\n\nNot ours.\n", encoding="utf-8")
    return target, outside


def _link(kind: str, target: Path, outside: Path, name: str) -> Path:
    where = {"outside": outside / "real.md", "inside": target / "docs" / "real.md", "dangling": outside / "gone.md"}[kind]
    link = target / name
    link.parent.mkdir(exist_ok=True)
    link.symlink_to(where)
    return link


def _snapshot(*roots: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


def _paths(seat: Burnish) -> list[str]:
    return [e.path for e in (*seat.code_edits, *seat.docs_edits)]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("method", ["finish", "finish_docs", "finish_code"])
@pytest.mark.parametrize("name", ["README.md", "readme"])
def test_a_readme_that_is_a_link_gets_no_edit(kind: str, method: str, name: str, tmp_path: Path):
    target, outside = _tree(tmp_path)
    link = _link(kind, target, outside, name)
    before = _snapshot(target, outside)
    seat = Burnish(scope="code")
    proposal = getattr(seat, method)(target, "base", FACTS)
    edited = [] if proposal is None else [e.path for e in proposal.edits]
    assert name not in edited and "README.md" not in edited
    assert not any((target / path).is_symlink() for path in edited + _paths(seat))
    assert "link" in " ".join(seat.notes) or method == "finish_code"
    # Nothing was written, and the link's target (outside the folder, or not there at all) is as it was.
    assert _snapshot(target, outside) == before and link.is_symlink()
    assert not (outside / "gone.md").exists()


@pytest.mark.parametrize("kind", KINDS)
def test_python_tidying_still_proposes_the_real_files_beside_a_readme_link(kind: str, tmp_path: Path):
    target, outside = _tree(tmp_path)
    _link(kind, target, outside, "README.md")
    proposal = Burnish(scope="code").finish(target, "base", FACTS)
    assert proposal is not None and [e.path for e in proposal.edits] == ["pkg/__init__.py"]


@pytest.mark.parametrize("kind", KINDS)
def test_a_python_file_that_is_a_link_or_lies_under_one_gets_no_edit(kind: str, tmp_path: Path):
    target, outside = _tree(tmp_path)
    (outside / "real.py").write_text(MODULE, encoding="utf-8")
    (target / "docs" / "inner.py").write_text(MODULE, encoding="utf-8")
    link = target / "linked.py"
    link.symlink_to({"outside": outside / "real.py", "inside": target / "docs" / "inner.py", "dangling": outside / "gone.py"}[kind])
    linked_dir = target / "linked_dir"
    linked_dir.symlink_to(outside if kind != "inside" else target / "docs", target_is_directory=True)
    before = _snapshot(outside)
    seat = Burnish(scope="code")
    seat.finish(target, "base", FACTS)
    assert not any(p in ("linked.py",) or p.startswith("linked_dir") for p in _paths(seat))
    assert _snapshot(outside) == before


@pytest.mark.parametrize("kind", KINDS)
def test_the_guard_drops_any_edit_whose_path_is_or_lies_under_a_link(kind: str, tmp_path: Path):
    """The rule itself, with edits the finder would never produce: a link as the file, and a link as a folder above it."""
    target, outside = _tree(tmp_path)
    file_link = _link(kind, target, outside, "README.md")
    dir_link = target / "via"
    dir_link.symlink_to(outside if kind != "inside" else target / "docs", target_is_directory=True)
    seat = Burnish(scope="code")
    kept = FileEdit(path="pkg/__init__.py", kind="write", new="x\n", old=MODULE)
    seat.code_edits = [kept, FileEdit(path="via/real.md", kind="write", new="x\n", old="")]
    seat.docs_edits = [FileEdit(path=file_link.name, kind="write", new="x\n", old="")]
    seat._drop_linked(target)
    assert seat.code_edits == [kept] and seat.docs_edits == []
    assert len(seat.notes) == 2 and all("symbolic link" in note for note in seat.notes)
