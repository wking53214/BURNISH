"""Campaign 3 of the 9.5 mission: the finisher writes nothing, and what it proposes cannot silently overwrite a change.

The read-only proof (`tests/test_read_only.py`) left `finish` out. This file closes that gap with the same two checks, the
photo of the tree and the tripwire that blocks every write anywhere on the machine, applied to every way the finisher is
run: the `burnish finish` preview, and the library calls Warden makes (`finish`, `finish_docs`, `finish_code`), in both
scopes, in this process and in a real child process. Planted writes of every kind the campaign names show the checks
catch a finisher that has started to write.

It also holds the proposal's integrity:

  * An edit to a file that exists is a `replace` of the file's whole text as it was read. Warden applies a `replace` only
    if that text is still there, so a file changed after the proposal is refused and put back, never overwritten. A
    `write` edit, which Warden applies whatever the file now holds, is used only for a file that did not exist (a new
    README) or was empty.
  * Every proposed edit has a record: the hashes of the text read and the text proposed, the lines that change, why, the
    protected-path decision, the scope and the baseline. `Burnish.stale` names every file that changed since.
  * The proposal boundary drops any edit that is absolute, climbs out with `..`, lands outside the target, is protected,
    or is under a link, whichever part of the finisher produced it.
  * The same tree gives the same proposal, record included, every time.

What this does not show: that native code (C extensions, `ctypes`) cannot write, since an audit hook sees only what Python
reports; that a new file cannot be created by someone else between the proposal and Warden's apply (Warden's `write` does
not check, and Burnish cannot change Warden; see the README); behaviour on Windows, where Warden does not run.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Callable, Optional

import pytest
from cns.seat import Facts, FileEdit
from cns.suite import SuiteRun
from test_read_only import TREES, WriteAttempt, differences, everything_tree, photo, run_in_process, tripwire
from warden.authorization import grant
from warden.tagteam import TagTeam

from burnish import cli, finisher
from burnish.finisher import Burnish, EditRecord

FACTS = Facts(suite=SuiteRun(ran=True, passed=2), remaining=(), cycles=1)
ROOT = Path(__file__).resolve().parent.parent

FINISH_RUNS: tuple[tuple[str, ...], ...] = (
    ("finish", "."),
    ("finish", ".", "--scope", "documentation"),
    ("finish", ".", "--scope", "code"),
    ("-v", "finish", "."),
)
SEATS = [(scope, method) for scope in ("documentation", "code") for method in ("finish", "finish_docs", "finish_code")]


def _tree(root: Path) -> None:
    """Code with whitespace to tidy, a test, and a hand-written README."""
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text('"""demo package."""\n\nVALUE = 1   \n', encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text("from pkg import VALUE\n\n\ndef test_a():\n    assert VALUE == 1\n",
                                              encoding="utf-8")
    (root / "README.md").write_text("# demo\n\nMy hand-written intro.\n\nMore of my words.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.0.1"\ndescription = "demo"\n',
                                         encoding="utf-8")


def finishable_tree(root: Path) -> None:
    """The everything tree plus a module with trailing whitespace, so both halves of the finisher have something to do."""
    everything_tree(root)
    (root / "demo" / "messy.py").write_text('"""Messy."""\n\nVALUE = 1   \n', encoding="utf-8")


FINISH_TREES = {**TREES, "finishable": finishable_tree}


def _auth(root: Path):
    return grant("william", "transform", str(root.resolve()), "code", "test")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------------------------------------------------
# The finisher writes nothing.

def _guarded_seat(root: Path, scope: str, method: str) -> tuple[bool, list[str], list[str]]:
    """Run one library call under the tripwire; return (a write was blocked, what was attempted, what changed)."""
    before = photo(root)
    blocked = False
    with contextlib.redirect_stdout(io.StringIO()), tripwire() as seen:
        try:
            getattr(Burnish(scope=scope), method)(root, "base", FACTS)
        except WriteAttempt:
            blocked = True
    return blocked, list(seen), differences(before, photo(root))


@pytest.mark.parametrize("label", list(FINISH_TREES))
def test_the_finish_preview_leaves_every_tree_exactly_as_it_was_and_writes_nowhere(label: str, tmp_path: Path):
    root = tmp_path / "tree"
    root.mkdir()
    FINISH_TREES[label](root)
    for argv in FINISH_RUNS:
        code, seen, changed = run_in_process(root, argv)
        assert (seen, changed) == ([], []), f"burnish {' '.join(argv)} on {label}"
        assert code in cli.EXIT_CODES


@pytest.mark.parametrize("label", list(FINISH_TREES))
def test_every_call_warden_makes_leaves_every_tree_exactly_as_it_was_and_writes_nowhere(label: str, tmp_path: Path):
    root = tmp_path / "tree"
    root.mkdir()
    FINISH_TREES[label](root)
    for scope, method in SEATS:
        assert _guarded_seat(root, scope, method) == (False, [], []), f"{method} scope={scope} on {label}"


def test_the_finisher_does_propose_on_the_trees_it_is_proven_on(tmp_path: Path):
    """A proof over trees where nothing is proposed would prove little: on the finishable tree both halves have edits."""
    finishable_tree(tmp_path)
    seat = Burnish(scope="code")
    seat.finish(tmp_path, "base", FACTS)
    assert seat.code_edits and seat.docs_edits


_CHILD = textwrap.dedent('''
    import os, sys
    from pathlib import Path
    seen = []
    def hook(event, args):
        if not armed:
            return
        flags = args[2] if event == "open" and len(args) > 2 else 0
        mode = args[1] if event == "open" and len(args) > 1 else None
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if (event == "open" and writing) or event.startswith(("os.", "shutil.", "tempfile.", "subprocess.")) and event not in (
                "os.listdir", "os.scandir", "os.walk", "os.chdir", "os.getcwd", "os.readlink", "os.add_dll_directory"):
            seen.append(event)
            raise RuntimeError("write blocked: " + event)
    armed = False
    sys.addaudithook(hook)
    from cns.seat import Facts
    from burnish.finisher import Burnish
    armed = True
    for scope in ("documentation", "code"):
        for method in ("finish", "finish_docs", "finish_code"):
            proposal = getattr(Burnish(scope=scope), method)(Path(sys.argv[1]), "base", Facts(suite=None, remaining=(), cycles=0))
            print(scope, method, 0 if proposal is None else len(proposal.edits))
    armed = False
    print("SEEN", seen)
''')


def test_as_a_real_process_the_finisher_writes_nothing_anywhere(tmp_path: Path):
    """A child process with its own tripwire armed after import: every call Warden makes, both scopes, on the everything
    tree. The photo is taken from outside the child."""
    root, script = tmp_path / "tree", tmp_path / "child.py"
    root.mkdir()
    finishable_tree(root)
    script.write_text(_CHILD, encoding="utf-8")
    before = photo(root)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run([sys.executable, "-I", str(script), str(root)], capture_output=True, text=True, timeout=120,
                          env=env)
    assert done.returncode == 0, done.stderr
    assert "SEEN []" in done.stdout
    assert "code finish 2" in done.stdout and "code finish_code 1" in done.stdout   # the calls did real work
    assert differences(before, photo(root)) == []


@pytest.mark.parametrize("argv", FINISH_RUNS, ids=[" ".join(a) for a in FINISH_RUNS])
def test_as_a_real_process_the_finish_preview_leaves_the_tree_exactly_as_it_was(argv: tuple[str, ...], tmp_path: Path):
    root = tmp_path / "tree"
    root.mkdir()
    finishable_tree(root)
    before = photo(root)
    done = subprocess.run([sys.executable, "-m", "burnish.cli", *argv], cwd=root, capture_output=True, text=True, timeout=120)
    assert done.returncode in cli.EXIT_CODES, done.stderr
    assert differences(before, photo(root)) == []


# ---------------------------------------------------------------------------------------------------------------------
# The checks catch a finisher that writes, by every mechanism the campaign names.

def _symlink(path: Path) -> None:
    path.symlink_to("README.md")


WRITES: dict[str, Callable[[Path], object]] = {
    "open for writing": lambda d: (d / "w.txt").open("w").close(),
    "open for appending": lambda d: (d / "kept").open("a").close(),
    "open read-write": lambda d: (d / "kept").open("r+").close(),
    "os.open create": lambda d: os.close(os.open(d / "raw", os.O_CREAT | os.O_WRONLY)),
    "os.open truncate": lambda d: os.close(os.open(d / "kept", os.O_WRONLY | os.O_TRUNC)),
    "os.remove": lambda d: os.remove(d / "kept"),
    "os.unlink": lambda d: os.unlink(d / "kept"),
    "os.rename": lambda d: os.rename(d / "kept", d / "moved"),
    "os.replace": lambda d: os.replace(d / "kept", d / "moved"),
    "os.truncate": lambda d: os.truncate(d / "kept", 0),
    "os.chmod": lambda d: os.chmod(d / "kept", 0o444),
    "os.link": lambda d: os.link(d / "kept", d / "hard"),
    "os.mkdir": lambda d: os.mkdir(d / "dir"),
    "shutil.copyfile": lambda d: shutil.copyfile(d / "kept", d / "copy"),
    "shutil.copy2": lambda d: shutil.copy2(d / "kept", d / "copy"),
    "shutil.move": lambda d: shutil.move(d / "kept", d / "moved"),
    "shutil.rmtree": lambda d: shutil.rmtree(d / "sub"),
    "tempfile.mkstemp": lambda d: os.close(tempfile.mkstemp(dir=d)[0]),
    "tempfile.NamedTemporaryFile": lambda d: tempfile.NamedTemporaryFile(dir=d).close(),
    "tempfile.TemporaryDirectory": lambda d: tempfile.TemporaryDirectory(dir=d).cleanup(),
    "a symbolic link": lambda d: (d / "alias.md").symlink_to(d / "kept"),
    "Path.write_bytes": lambda d: (d / "kept").write_bytes(b"x"),
    "another program": lambda d: subprocess.run(["true"], check=False),
}


def _planted(where: str, root: Path, elsewhere: Path, act: Callable[[Path], object]):
    """A `Burnish.finish` that writes with `act` (inside the tree or elsewhere) before it proposes."""
    real = Burnish.finish

    def writing_finish(self, target, baseline, facts):
        folder = root if where == "inside" else elsewhere
        act(folder)
        return real(self, target, baseline, facts)

    return writing_finish


@pytest.mark.parametrize("where", ["inside", "outside"])
@pytest.mark.parametrize("kind", list(WRITES))
def test_the_tripwire_blocks_a_finisher_that_writes(kind: str, where: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root, elsewhere = tmp_path / "tree", tmp_path / "elsewhere"
    for folder in (root, elsewhere):
        folder.mkdir()
        (folder / "kept").write_text("x", encoding="utf-8")
        (folder / "sub").mkdir()
        (folder / "sub" / "f").write_text("y", encoding="utf-8")
    _tree(root)
    left = photo(elsewhere)
    monkeypatch.setattr(Burnish, "finish", _planted(where, root, elsewhere, WRITES[kind]))
    code, seen, changed = run_in_process(root, ["finish", ".", "--scope", "code"])
    assert code is None and seen, f"{kind} {where} was not blocked"
    assert changed == [] and differences(left, photo(elsewhere)) == []   # blocked, not merely noticed


@pytest.mark.parametrize("kind", ["open for writing", "os.replace", "shutil.rmtree", "tempfile.mkstemp"])
def test_the_photo_alone_catches_a_finisher_that_writes_inside_the_tree(kind: str, tmp_path: Path,
                                                                        monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "tree"
    root.mkdir()
    _tree(root)
    (root / "kept").write_text("x", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "f").write_text("y", encoding="utf-8")
    monkeypatch.setattr(Burnish, "finish", _planted("inside", root, root, WRITES[kind]))
    _, seen, changed = run_in_process(root, ["finish", ".", "--scope", "code"], guarded=False)
    assert seen == [] and changed


# ---------------------------------------------------------------------------------------------------------------------
# A proposal cannot overwrite a change made after it.

def _apply(root: Path, proposal) -> None:
    proposal.authorize(_auth(root))
    proposal.apply(root)


def test_every_edit_to_a_file_that_exists_replaces_the_whole_text_as_it_was_read(tmp_path: Path):
    _tree(tmp_path)
    proposal = Burnish(scope="code").finish(tmp_path, "base", FACTS)
    assert proposal is not None and len(proposal.edits) == 2
    for edit in proposal.edits:
        assert edit.kind == "replace" and not edit.replace_all
        assert edit.old.encode("utf-8") == (tmp_path / edit.path).read_bytes()


def test_a_new_readme_is_the_only_write(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "README.md").unlink()
    proposal = Burnish(scope="code").finish(tmp_path, "base", FACTS)
    assert proposal is not None
    assert {(e.path, e.kind) for e in proposal.edits} == {("pkg/__init__.py", "replace"), ("README.md", "write")}


@pytest.mark.parametrize("path", ["README.md", "pkg/__init__.py"])
def test_a_file_changed_after_the_proposal_is_refused_by_warden_not_overwritten(path: str, tmp_path: Path):
    _tree(tmp_path)
    proposal = Burnish(scope="code").finish_docs(tmp_path, "base", FACTS) if path == "README.md" else \
        Burnish(scope="code").finish_code(tmp_path, "base", FACTS)
    assert proposal is not None
    changed = (tmp_path / path).read_text(encoding="utf-8").replace("1", "2").replace("hand-written", "edited")
    (tmp_path / path).write_text(changed, encoding="utf-8")
    with pytest.raises(ValueError, match="preservation check failed"):
        _apply(tmp_path, proposal)
    assert (tmp_path / path).read_text(encoding="utf-8") == changed


def test_a_file_deleted_after_the_proposal_is_not_recreated(tmp_path: Path):
    _tree(tmp_path)
    proposal = Burnish(scope="code").finish_docs(tmp_path, "base", FACTS)
    assert proposal is not None
    (tmp_path / "README.md").unlink()
    with pytest.raises(FileNotFoundError):
        _apply(tmp_path, proposal)
    assert not (tmp_path / "README.md").exists()


def test_text_added_around_the_original_after_the_proposal_is_kept_not_lost(tmp_path: Path):
    """Warden's replace looks for the original text inside the file, so an addition before or after it survives: the
    other writer's text is kept, which is the boundary of this guarantee (a merge, not a refusal), stated in the README."""
    _tree(tmp_path)
    proposal = Burnish().finish_docs(tmp_path, "base", FACTS)
    assert proposal is not None
    readme = tmp_path / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nAdded by someone else.\n", encoding="utf-8")
    _apply(tmp_path, proposal)
    text = readme.read_text(encoding="utf-8")
    assert "Added by someone else." in text and "My hand-written intro." in text and "## Measured facts (generated)" in text


def _another_writer_before_warden_applies(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Edit the README after the finisher has handed over its proposal and before Warden applies it: another process, not
    the finisher (Warden undoes and rejects any change the finisher makes while it has control). Returns a list that gets
    the README's text as it stood right after Warden's apply step, before the end of the run.

    The end of the run is not where to look: a run that does not end in a full ACCEPT puts the whole folder back as it
    was found, which also undoes the other writer's change. That is Warden's, recorded in the README as a Warden finding.
    """
    real = TagTeam._apply
    after_apply: list[str] = []

    def apply_after_someone_else(self, target, proposal, *args, **kwargs):
        readme = Path(target) / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("More of my words.", "Someone else's words."),
                          encoding="utf-8")
        done = real(self, target, proposal, *args, **kwargs)
        after_apply.append(readme.read_text(encoding="utf-8"))
        return done

    monkeypatch.setattr(TagTeam, "_apply", apply_after_someone_else)
    return after_apply


class _Idle:
    """A drafter with nothing to propose, so the loop converges at once."""

    def propose(self, target, observed, baseline):
        return None


def test_through_warden_a_concurrent_change_puts_the_whole_finish_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The code tidy is applied first; the README edit then fails Warden's preservation check, and Warden puts both back,
    keeping the other writer's text. The rollback is Warden's; this shows Burnish's proposal lets it happen."""
    _tree(tmp_path)
    code_before = (tmp_path / "pkg" / "__init__.py").read_bytes()
    after_apply = _another_writer_before_warden_applies(monkeypatch)
    result = TagTeam(drafter=_Idle(), finisher=Burnish(scope="code")).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "FINISH_REJECTED" and "PUT_BACK" in result.reason, result.reason
    (readme,) = after_apply
    assert "Someone else's words." in readme and "## Measured facts (generated)" not in readme
    assert (tmp_path / "pkg" / "__init__.py").read_bytes() == code_before


def test_without_the_replace_the_same_concurrent_change_would_have_been_lost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The control: the proposal as it was before this change (a write of the whole file) lets Warden overwrite the other
    writer's text. This is the defect the replace closes, kept as a test so the reason for the design stays visible."""
    _tree(tmp_path)
    monkeypatch.setattr(Burnish, "_guard", Burnish._drop_linked)
    after_apply = _another_writer_before_warden_applies(monkeypatch)
    TagTeam(drafter=_Idle(), finisher=Burnish()).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    (readme,) = after_apply
    assert "## Measured facts (generated)" in readme and "Someone else's words." not in readme


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
@pytest.mark.parametrize("bom", ["", "﻿"])
def test_line_endings_and_a_bom_still_apply_and_finish_to_a_fixed_point(ending: str, bom: str, tmp_path: Path):
    _tree(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_bytes((bom + "# demo\n\nMy hand-written intro.\n").replace("\n", ending).encode("utf-8"))
    code = tmp_path / "pkg" / "__init__.py"
    code.write_bytes('"""demo package."""\n\nVALUE = 1   \n'.replace("\n", ending).encode("utf-8"))
    proposal = Burnish(scope="code").finish(tmp_path, "base", FACTS)
    assert proposal is not None
    _apply(tmp_path, proposal)
    assert readme.read_bytes().startswith((bom + "# demo" + ending + ending + "My hand-written intro.").encode("utf-8"))
    assert code.read_bytes() == '"""demo package."""\n\nVALUE = 1\n'.replace("\n", ending).encode("utf-8")
    assert Burnish(scope="code").finish(tmp_path, "base", FACTS) is None


# ---------------------------------------------------------------------------------------------------------------------
# Every edit has a record, and the record says when it is stale.

def test_every_proposed_edit_has_a_record_that_matches_it(tmp_path: Path):
    _tree(tmp_path)
    seat = Burnish(scope="code")
    proposal = seat.finish(tmp_path, "tree-fingerprint", FACTS)
    assert proposal is not None
    records = {r.path: r for r in seat.records}
    assert set(records) == {e.path for e in proposal.edits}
    for edit in proposal.edits:
        record = records[edit.path]
        assert isinstance(record, EditRecord)
        assert record.kind == edit.kind
        assert record.original_sha256 == _sha((tmp_path / edit.path).read_bytes())
        assert record.proposed_sha256 == _sha(edit.new.encode("utf-8"))
        assert record.protected is False and record.scope == "code" and record.baseline == "tree-fingerprint"
        assert record.original_sha256 in proposal.architectural_reason
        assert record.proposed_sha256 in proposal.architectural_reason
    assert records["pkg/__init__.py"].changed_lines == ((3, 3),)
    assert "tidy" in records["pkg/__init__.py"].reason and "README" in records["README.md"].reason


def test_a_new_file_is_recorded_as_having_no_original(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "README.md").unlink()
    seat = Burnish()
    seat.finish(tmp_path, "base", FACTS)
    (record,) = [r for r in seat.records if r.path == "README.md"]
    assert record.original_sha256 is None and record.kind == "write"


def test_stale_names_every_file_changed_deleted_or_created_since_the_proposal(tmp_path: Path):
    _tree(tmp_path)
    seat = Burnish(scope="code")
    seat.finish(tmp_path, "base", FACTS)
    assert seat.stale(tmp_path) == []
    (tmp_path / "pkg" / "__init__.py").write_text("VALUE = 2\n", encoding="utf-8")
    (tmp_path / "README.md").unlink()
    assert seat.stale(tmp_path) == ["README.md", "pkg/__init__.py"]
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    _tree(fresh)
    (fresh / "README.md").unlink()
    seat.finish(fresh, "base", FACTS)
    (fresh / "README.md").write_text("# someone else's\n", encoding="utf-8")
    assert seat.stale(fresh) == ["README.md"]


def test_records_left_out_of_the_proposal_are_not_listed(tmp_path: Path):
    """Under a documentation grant the code edits are computed but not proposed; the records are of what is proposed."""
    _tree(tmp_path)
    seat = Burnish()
    proposal = seat.finish(tmp_path, "base", FACTS)
    assert proposal is not None and seat.code_edits
    assert [r.path for r in seat.records] == [e.path for e in proposal.edits] == ["README.md"]


def test_the_same_tree_gives_the_same_proposal_and_records_every_time(tmp_path: Path):
    _tree(tmp_path)
    runs = []
    for _ in range(3):
        seat = Burnish(scope="code")
        proposal = seat.finish(tmp_path, "base", FACTS)
        assert proposal is not None
        runs.append((proposal.edits, proposal.architectural_reason, tuple(seat.records)))
    assert runs[0] == runs[1] == runs[2]


# ---------------------------------------------------------------------------------------------------------------------
# The proposal boundary.

UNSAFE = {
    "../escape.py": "outside",
    "pkg/../../escape.py": "outside",
    "/etc/escape.py": "absolute",
    "tests/test_x.py": "protected",
    ".github/workflows/ci.yml": "protected",
    "pkg/conftest.py": "protected",
}


@pytest.mark.parametrize("path", list(UNSAFE))
def test_an_unsafe_edit_from_any_part_of_the_finisher_is_dropped_at_the_boundary(path: str, tmp_path: Path,
                                                                                  monkeypatch: pytest.MonkeyPatch):
    _tree(tmp_path)
    real = finisher.tidy_edits

    def with_a_bad_edit(root: Path, notes: Optional[list[str]] = None) -> list[FileEdit]:
        return [*real(root, notes), FileEdit(path=path, kind="write", new="x = 1\n", old="")]

    monkeypatch.setattr(finisher, "tidy_edits", with_a_bad_edit)
    seat = Burnish(scope="code")
    proposal = seat.finish(tmp_path, "base", FACTS)
    assert proposal is not None
    assert path not in [e.path for e in proposal.edits] + [e.path for e in seat.code_edits]
    assert {e.path for e in proposal.edits} == {"pkg/__init__.py", "README.md"}
    assert any(path in note and UNSAFE[path] in note for note in seat.notes), seat.notes


def test_an_absolute_path_through_a_link_is_named_absolute_not_a_link(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """On macOS `/etc` is a link to `/private/etc`, and CI there showed the reason given was "a link". The spelling decides
    first, so the reason is the same on every system. This builds the same case on any system."""
    root, real_dir = tmp_path / "tree", tmp_path / "real"
    root.mkdir()
    real_dir.mkdir()
    _tree(root)
    (tmp_path / "alias").symlink_to(real_dir, target_is_directory=True)
    bad = str(tmp_path / "alias" / "escape.py")
    real = finisher.tidy_edits
    monkeypatch.setattr(finisher, "tidy_edits", lambda r, notes=None: [*real(r, notes), FileEdit(path=bad, kind="write", new="x")])
    seat = Burnish(scope="code")
    seat.finish(root, "base", FACTS)
    assert [note for note in seat.notes if bad in note] == [f"{bad} is an absolute path, so no edit was proposed for it."]


def test_the_boundary_and_warden_agree_that_an_escape_is_refused(tmp_path: Path):
    """Belt and braces: even if an escaping edit reached Warden, Warden would refuse it."""
    _tree(tmp_path)
    proposal = Burnish(scope="code").finish(tmp_path, "base", FACTS)
    assert proposal is not None
    from warden.models import Unauthorized
    bad = proposal.__class__(**{**proposal.__dict__, "edits": (FileEdit(path="../escape.py", kind="write", new="x"),)})
    with pytest.raises(Unauthorized):
        _apply(tmp_path, bad)
    assert not (tmp_path.parent / "escape.py").exists()


#: Names that are a file operation whatever they are called on.
_ALWAYS_WRITES = frozenset({"write_text", "write_bytes", "unlink", "rmtree", "mkdir", "makedirs", "rmdir", "symlink_to",
                            "hardlink_to", "touch", "chmod", "lchmod", "mkstemp", "mkdtemp", "NamedTemporaryFile",
                            "TemporaryFile", "TemporaryDirectory", "SpooledTemporaryFile", "copyfile", "copytree", "copy2",
                            "copymode", "copystat", "mkfifo", "mknod", "utime", "ftruncate"})
#: Names that are also ordinary methods (`str.replace`, `list.remove`, `dict.copy`): a file operation when called on a
#: module that writes files.
_WRITES_ON_A_FILE_MODULE = frozenset({"replace", "rename", "renames", "remove", "removedirs", "copy", "move", "link",
                                      "symlink", "truncate", "open", "system", "popen", "run", "Popen", "call",
                                      "check_call", "check_output", "spawnv", "execv", "fork", "posix_spawn"})
_FILE_MODULES = frozenset({"os", "shutil", "tempfile", "subprocess", "io", "pathlib"})


def _opens_to_write(node: ast.Call) -> bool:
    """True for an `open(...)` call whose mode writes, or whose mode cannot be read from the source."""
    modes = list(node.args[1:2]) + [k.value for k in node.keywords if k.arg == "mode"]
    return any(not isinstance(m, ast.Constant) or not isinstance(m.value, str) or any(c in m.value for c in "wax+")
               for m in modes)


def test_the_package_has_no_call_that_writes_files_by_any_python_mechanism():
    """A source search backing the runtime proof: no call in the package writes, renames, removes or makes a file, or
    starts a program. The runtime proof above is the evidence; this catches a new call in code the trees do not reach."""
    found = []
    for path in sorted((ROOT / "burnish").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            receiver = func.value.id if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) else ""
            if name in _ALWAYS_WRITES or (name in _WRITES_ON_A_FILE_MODULE and receiver in _FILE_MODULES):
                found.append(f"{path.name}:{node.lineno} {receiver + '.' if receiver else ''}{name}")
            elif name == "open" and _opens_to_write(node):
                found.append(f"{path.name}:{node.lineno} open")
    assert found == []
