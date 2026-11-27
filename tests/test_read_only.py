"""Item 19 of the remediation plan: every read-only command leaves the tree it reads exactly as it was, and writes nowhere else.

The read-only commands are every command but `finish` (the owner's narrowing). Each one runs, with its options, on every
planted repository, every CNS example tree and one tree with a bit of everything in it. Two checks watch each run:

  * a photo of the tree before and after: every file, folder and link, its kind, permissions, size, modification and
    change times, and its contents (or a link's target). Only the access time is left out, because reading changes it.
    A folder's times are in the photo too, so a file created and then deleted still shows.
  * a tripwire: a Python audit hook that, while the command runs, blocks and records any attempt anywhere on the machine
    to open a file for writing, create, rename, delete, truncate or change a file or folder, or start another program.
    Bytecode caching is turned off for the run so Python's own import machinery does not trip it.

Each command also runs once as a real process on the everything tree, under the photo check. Tests at the end plant writes
of each kind and show that the checks catch them, so a pass cannot come from checks that see nothing.

What this does not show: that `finish` writes nothing, behaviour on other operating systems, or every possible input.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import io
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterator, Optional, Sequence

import pytest
from test_cns_examples import EXAMPLES
from test_planted import collection

from burnish import cli

READ_ONLY = frozenset({"check", "critic", "readme-critic", "inspect", "readme", "cns", "criteria", "languages"})
OUT_OF_SCOPE = frozenset({"finish"})   # the owner's narrowing of item 19

#: Every way a read-only command is run here. Paths are "." because each run starts in the tree's own folder, which is
#: also where `criteria` and `languages`, which take no path, run.
RUNS: tuple[tuple[str, ...], ...] = (
    ("check", "."),
    ("critic", "."),
    ("critic", ".", "--collected", "3"),
    ("-v", "critic", "."),
    ("readme-critic", ".", "--tier", "minimum"),
    ("readme-critic", ".", "--tier", "strong"),
    ("readme-critic", ".", "--tier", "over-the-top", "--collected", "3"),
    ("inspect", "."),
    ("readme", "."),
    ("-v", "cns", "."),
    ("criteria",),
    ("languages",),
)

# ---------------------------------------------------------------------------------------------------------------------
# The tripwire. An audit hook cannot be removed once added, so it is added once and switched on only for one run.

_WRITE_EVENTS = frozenset({
    "os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.symlink", "os.link", "os.chmod", "os.chown", "os.chflags",
    "os.lchflags", "os.lchown", "os.utime", "os.truncate", "os.setxattr", "os.removexattr", "os.mkfifo", "os.mknod",
    "shutil.copyfile", "shutil.copymode", "shutil.copystat", "shutil.copytree", "shutil.move", "shutil.rmtree",
    "shutil.chown", "shutil.make_archive", "shutil.unpack_archive", "tempfile.mkstemp", "tempfile.mkdtemp",
})
_PROGRAM_EVENTS = frozenset({"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty"})
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


class WriteAttempt(RuntimeError):
    """Raised inside a guarded run to block a write. Not an OSError, so no handler meant for a failed read can swallow it."""


class _Wire:
    on = False
    seen: list[str] = []


def _opens_for_writing(args: tuple[object, ...]) -> bool:
    mode = args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else 0
    return (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and bool(flags & _WRITE_FLAGS))


def _hook(event: str, args: tuple[object, ...]) -> None:
    if not _Wire.on:
        return
    if (event == "open" and _opens_for_writing(args)) or event in _WRITE_EVENTS or event in _PROGRAM_EVENTS:
        _Wire.seen.append(f"{event} {args[0] if args else ''}")
        raise WriteAttempt(event)


sys.addaudithook(_hook)


@contextlib.contextmanager
def tripwire() -> Iterator[list[str]]:
    """Block and record every write while the block runs; yields the list of what was attempted."""
    seen: list[str] = []
    cached = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    _Wire.seen, _Wire.on = seen, True
    try:
        yield seen
    finally:
        _Wire.on = False
        sys.dont_write_bytecode = cached


# ---------------------------------------------------------------------------------------------------------------------
# The photo.

Photo = dict[str, tuple[object, ...]]


def photo(root: Path) -> Photo:
    """Everything about a tree a write could change, except access times. The root folder itself is the entry "."."""
    taken: Photo = {}
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in [".", *dirs, *files] if Path(folder) == root else [*dirs, *files]:
            path = Path(folder) / name if name != "." else root
            st = path.lstat()
            if stat.S_ISLNK(st.st_mode):
                body: Optional[str] = "-> " + os.readlink(path)
            elif stat.S_ISREG(st.st_mode):
                body = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                body = None
            taken[path.relative_to(root).as_posix()] = (
                stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode), st.st_size, st.st_mtime_ns, st.st_ctime_ns, body)
    return taken


def differences(before: Photo, after: Photo) -> list[str]:
    return ([f"added {p}" for p in sorted(after.keys() - before.keys())]
            + [f"deleted {p}" for p in sorted(before.keys() - after.keys())]
            + [f"changed {p}" for p in sorted(before.keys() & after.keys()) if before[p] != after[p]])


# ---------------------------------------------------------------------------------------------------------------------
# One run, in this process.

def run_in_process(root: Path, argv: Sequence[str], guarded: bool = True) -> tuple[Optional[int], list[str], list[str]]:
    """Run one command in `root`; return its exit code (None if a write was blocked), what the tripwire saw, what changed."""
    before = photo(root)
    home = os.getcwd()
    os.chdir(root)
    code: Optional[int] = None
    try:
        guard: contextlib.AbstractContextManager[list[str]] = tripwire() if guarded else contextlib.nullcontext([])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), guard as seen:
            try:
                code = cli.main(list(argv))
            except WriteAttempt:
                code = None
    finally:
        os.chdir(home)
    return code, list(seen), differences(before, photo(root))


def problems_on(root: Path, label: str) -> list[str]:
    """Every read-only run on one tree; what went wrong, each line naming the command, the tree and the path."""
    found: list[str] = []
    for argv in RUNS:
        code, seen, changed = run_in_process(root, argv)
        command = "burnish " + " ".join(argv)
        found += [f"{command} on {label}: tried {attempt}" for attempt in seen]
        found += [f"{command} on {label}: {change}" for change in changed]
        if not seen and code not in cli.EXIT_CODES:
            found.append(f"{command} on {label}: exit code {code} is not one Burnish defines")
    return found


# ---------------------------------------------------------------------------------------------------------------------
# The sample trees.

def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def everything_tree(root: Path) -> None:
    """A tree with a bit of everything a command reads: metadata, a README with claims, PROVENANCE, code with findings,
    an import of cns, a file that is not UTF-8, tests, docs, hidden files, an empty folder, links and a read-only file."""
    _write(root, {
        "pyproject.toml": ('[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["click>=8"]\n\n'
                           '[project.optional-dependencies]\ncns = ["cns @ git+https://github.com/wking53214/CNS.git@v4.1.0"]\n'),
        "README.md": ("# demo\n\nDemo has 3 tests and is production ready.\n\n## Install\n\n    pip install demo\n\n"
                      "See [the guide](docs/guide.md). It does not talk to the network.\n"),
        "PROVENANCE.md": "# Provenance\n\nWritten for this test.\n",
        "demo/__init__.py": '"""Demo."""\n',
        "demo/core.py": "def Bad(x):\n    try:\n        return x == None\n    except:\n        pass\n",
        "demo/seam.py": '"""Seam."""\ntry:\n    import cns\nexcept ImportError:\n    cns = None\n',
        "tests/test_core.py": "def test_one():\n    assert True\n",
        "docs/guide.md": "# Guide\n",
        ".hidden/config": "x = 1\n",
        ".gitignore": "build/\n",
    })
    (root / "demo" / "latin1.py").write_bytes(b"# caf\xe9\nX = 1\n")
    (root / "empty").mkdir()
    (root / "link.py").symlink_to("demo/core.py")
    (root / "alias").symlink_to("demo", target_is_directory=True)
    locked = root / "demo" / "locked.py"
    locked.write_text('"""Read-only file."""\n', encoding="utf-8")
    locked.chmod(0o444)


PLANTED = {f"planted/{p.name}": p.files for p in collection()}
CNS_TREES = {f"cns example: {name}": files for name, (files, _) in EXAMPLES.items()}
TREES: dict[str, Callable[[Path], object]] = {
    "everything": everything_tree,
    **{label: functools.partial(_write, files=files) for label, files in {**PLANTED, **CNS_TREES}.items()},
}


# ---------------------------------------------------------------------------------------------------------------------
# The proof.

def test_every_command_is_either_read_only_or_named_out_of_scope():
    """A new command fails this until someone decides which list it belongs to, so it cannot slip past the proof."""
    commands = {name for action in cli._parser()._actions if isinstance(action, argparse._SubParsersAction)
                for name in action.choices}
    assert commands == READ_ONLY | OUT_OF_SCOPE
    assert not READ_ONLY & OUT_OF_SCOPE


def test_every_read_only_command_is_run_here():
    ran = {next(arg for arg in argv if not arg.startswith("-")) for argv in RUNS}
    assert ran == READ_ONLY


@pytest.mark.parametrize("label", list(TREES))
def test_every_read_only_command_leaves_the_tree_exactly_as_it_was_and_writes_nowhere(label: str, tmp_path: Path):
    root = tmp_path / "tree"
    root.mkdir()
    TREES[label](root)
    assert problems_on(root, label) == []


@pytest.mark.parametrize("argv", RUNS, ids=[" ".join(a) for a in RUNS])
def test_as_a_real_process_every_read_only_command_leaves_the_tree_exactly_as_it_was(argv: tuple[str, ...], tmp_path: Path):
    root = tmp_path / "tree"
    root.mkdir()
    everything_tree(root)
    before = photo(root)
    done = subprocess.run([sys.executable, "-m", "burnish.cli", *argv], cwd=root, capture_output=True, text=True, timeout=120)
    assert done.returncode in cli.EXIT_CODES, done.stderr
    assert differences(before, photo(root)) == []


# ---------------------------------------------------------------------------------------------------------------------
# The checks catch what they are meant to catch.

def _replace_check(monkeypatch: pytest.MonkeyPatch, act: Callable[[Path], object]) -> None:
    """Make `burnish check` do `act` to its folder before it checks, standing in for a command that has started to write."""
    real = cli._check

    def writing_check(args: argparse.Namespace) -> int:
        act(Path(args.path))
        return real(args)

    monkeypatch.setattr(cli, "_check", writing_check)


def _make_and_remove(root: Path) -> None:
    (root / "scratch").write_text("x", encoding="utf-8")
    (root / "scratch").unlink()


INSIDE_WRITES: dict[str, tuple[Callable[[Path], object], str]] = {
    "a new file": (lambda root: (root / "new.txt").write_text("x", encoding="utf-8"), "added new.txt"),
    "an edited file": (lambda root: (root / "demo" / "core.py").write_text("x = 1\n", encoding="utf-8"), "changed demo/core.py"),
    "a deleted file": (lambda root: (root / "docs" / "guide.md").unlink(), "deleted docs/guide.md"),
    "a new folder": (lambda root: (root / "build").mkdir(), "added build"),
    "a file made and removed": (_make_and_remove, "changed ."),
    "a touched file": (lambda root: os.utime(root / "README.md", ns=(0, 1)), "changed README.md"),
    "a changed permission": (lambda root: (root / "README.md").chmod(0o600), "changed README.md"),
}


@pytest.mark.parametrize("kind", list(INSIDE_WRITES))
def test_the_photo_alone_catches_each_kind_of_change_inside_the_tree(kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    act, expected = INSIDE_WRITES[kind]
    everything_tree(tmp_path)
    _replace_check(monkeypatch, act)
    _, seen, changed = run_in_process(tmp_path, ["check", "."], guarded=False)
    assert seen == [] and expected in changed


@pytest.mark.parametrize("kind", list(INSIDE_WRITES))
def test_the_tripwire_alone_blocks_each_kind_of_change_inside_the_tree(kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    act, _ = INSIDE_WRITES[kind]
    everything_tree(tmp_path)
    _replace_check(monkeypatch, act)
    code, seen, changed = run_in_process(tmp_path, ["check", "."])
    assert code is None and seen and changed == []


OUTSIDE_WRITES: dict[str, Callable[[Path], object]] = {
    "a file opened for writing": lambda elsewhere: (elsewhere / "cache.txt").open("w").close(),
    "a file opened for appending": lambda elsewhere: (elsewhere / "log.txt").open("a").close(),
    "a low-level create": lambda elsewhere: os.close(os.open(elsewhere / "raw", os.O_CREAT | os.O_WRONLY)),
    "a new folder": lambda elsewhere: (elsewhere / "dir").mkdir(),
    "a rename": lambda elsewhere: os.rename(elsewhere / "kept", elsewhere / "moved"),
    "a delete": lambda elsewhere: (elsewhere / "kept").unlink(),
    "another program": lambda elsewhere: subprocess.run(["true"], check=False),
}


@pytest.mark.parametrize("kind", list(OUTSIDE_WRITES))
def test_the_tripwire_blocks_a_write_outside_the_tree_that_the_photo_cannot_see(kind: str, tmp_path: Path,
                                                                               monkeypatch: pytest.MonkeyPatch):
    root, elsewhere = tmp_path / "tree", tmp_path / "elsewhere"
    root.mkdir()
    elsewhere.mkdir()
    everything_tree(root)
    (elsewhere / "kept").write_text("x", encoding="utf-8")
    left = photo(elsewhere)
    _replace_check(monkeypatch, lambda _root: OUTSIDE_WRITES[kind](elsewhere))
    code, seen, changed = run_in_process(root, ["check", "."])
    assert code is None and seen and changed == []
    assert differences(left, photo(elsewhere)) == []   # blocked, not merely noticed


def test_a_write_is_reported_with_the_command_the_tree_and_the_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    everything_tree(tmp_path)
    _replace_check(monkeypatch, lambda root: (root / "new.txt").write_text("x", encoding="utf-8"))
    found = problems_on(tmp_path, "everything")
    assert any(line.startswith("burnish check . on everything: tried open") and "new.txt" in line for line in found)
