"""burnish: read a tree, say what is wrong with it, plainly.

Every command here only reads. Changing a repository is Warden's job and
needs a human grant; `warden tagteam --finisher burnish.finisher:Burnish`
is how Burnish's one-time finishing proposal reaches a file.

EXIT CODES
  0  nothing to report at the level asked for
  1  findings (or a README below the requested tier)
  2  could not run (bad usage, a path that is missing or unreadable, or a path with nothing to check)
  3  the report could not be delivered (standard output closed or full) and the check itself would have exited 0

A command that cannot look at anything never reports a clean result: "0 findings" over a tree
that was not read would be a lie, so it exits 2 and says why on stderr.

A report that cannot be delivered is never a silent success either. If the reader of a pipe went away
(`burnish critic . | head`) the output is cut short, one line on stderr says so, and the exit code stays the one
the check earned, as `head` itself intends. For any other failure to write standard output (closed, full device) the
line says why, an earned 1 or 2 stays as it is, and an earned 0 becomes 3.

LOGGING
  Messages go to stderr. `--verbose` shows the debug trail; `BURNISH_LOG_LEVEL`
  (DEBUG, INFO, WARNING, ERROR or CRITICAL) sets the level when `--verbose` is not given.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Sequence, TextIO, cast

from . import __version__
from .checks import check_tree, checkable_files, summarize
from .cns_boundary import analyse as cns_analyse
from .cns_boundary import to_dict as cns_to_dict
from cns.seat import Facts

from .criteria import CRITERIA
from .critic import PoetryCritic
from .drift import check_test_claims, check_tree_claims
from .files import broken_python_links, broken_readme_links, find_readme, python_files
from .finisher import Burnish
from .languages import describe
from .narrative import inspect_tree
from .readme import compile_readme
from .readme_critic import ReadmeCritic, Tier

_TIERS = {"minimum": Tier.MINIMUM, "strong": Tier.STRONG, "over-the-top": Tier.OVER_THE_TOP}

EXIT_OK, EXIT_FINDINGS, EXIT_CANNOT_RUN, EXIT_NOT_DELIVERED = 0, 1, 2, 3

#: The exit codes, as the README's table states them. A test keeps the two in step.
EXIT_CODES = {
    EXIT_OK: "Nothing to report at the level asked for.",
    EXIT_FINDINGS: "Findings, or a README below the requested tier, or a README claim the tree contradicts.",
    EXIT_CANNOT_RUN: "Could not run: bad usage, a path that is missing or unreadable, or a path with nothing to check.",
    EXIT_NOT_DELIVERED: "The report could not be delivered (standard output closed or full) and the check itself would have exited 0.",
}

LOG_LEVEL_ENV = "BURNISH_LOG_LEVEL"
_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
log = logging.getLogger("burnish")

#: What each command that takes a path needs to find there, or it exits 2: Python files, a README, or either.
_NEEDS = {"check": "python", "critic": "either", "readme-critic": "readme", "inspect": "either",
          "readme": "either", "finish": "either", "cns": "either"}


class CannotRun(Exception):
    """The command could not look at what it was pointed at; main turns this into exit code 2."""


class _Stdout(io.StringIO):
    """Standard output for the length of one command: forwards everything, remembers the first failure, drops the rest.

    A command prints as it goes. If the reader has gone, the stream is closed or the device is full, the command still has
    to finish, because the exit code it earned does not depend on whether anyone could read the report.
    """

    def __init__(self, stream: Optional[TextIO]) -> None:
        super().__init__()
        self._stream = stream
        self.failure: Optional[Exception] = None

    def write(self, text: str) -> int:
        if text and self.failure is None:
            try:
                if self._stream is None:
                    raise OSError(errno.EBADF, "standard output is closed")
                self._stream.write(text)
            except (OSError, ValueError) as error:   # ValueError: a closed file object, or text the stream cannot encode
                self.failure = error
        return len(text)

    def flush(self) -> None:
        if self.failure is None and self._stream is not None:
            try:
                self._stream.flush()
            except (OSError, ValueError) as error:
                self.failure = error


def run(argv: Optional[Sequence[str]] = None) -> int:
    """Run one command as the process's own entry point (the console script and `python -m burnish.cli`).

    Like `main`, but a standard output that failed is replaced by None before returning, so the flush the interpreter does at
    exit does not fail a second time (exit status 120). `main` leaves the stream as it found it, for a caller in the same process.
    """
    return main(argv, _as_process=True)


def main(argv: Optional[Sequence[str]] = None, *, _as_process: bool = False) -> int:
    """Run one command and return its exit code (see EXIT_CODES)."""
    parser = _parser()
    out = _Stdout(sys.stdout)
    try:
        with contextlib.redirect_stdout(out):   # --version and --help print too, then exit
            args = parser.parse_args(argv)
    except SystemExit as stop:
        raise SystemExit(_settle(out, "burnish", stop.code if isinstance(stop.code, int) else EXIT_OK, _as_process)) from None
    handlers = {
        "check": _check, "critic": _critic, "readme-critic": _readme_critic, "inspect": _inspect,
        "readme": _readme, "finish": _finish, "cns": _cns, "criteria": _criteria, "languages": _languages,
    }
    try:
        _configure_logging(getattr(args, "verbose", False))
        log.debug("command=%s path=%s", args.command, getattr(args, "path", None))
        if args.command in _NEEDS:
            _require_something_to_read(args.command, args.path)
        with contextlib.redirect_stdout(out):
            code = handlers[args.command](args)
    except CannotRun as error:
        print(f"burnish {args.command}: {error}", file=sys.stderr)
        code = EXIT_CANNOT_RUN
    except OSError as error:
        if error.filename is None:   # not a file that could not be read (for example a closed pipe)
            raise
        print(f"burnish {args.command}: cannot read {error.filename or 'a file'}: {error.strerror or error}", file=sys.stderr)
        code = EXIT_CANNOT_RUN
    code = _settle(out, f"burnish {args.command}", code, _as_process)
    log.info("exit code %d: %s", code, EXIT_CODES[code])
    return code


def _settle(out: _Stdout, who: str, code: int, as_process: bool = False) -> int:
    """Flush the report and say so on stderr if it did not arrive; an earned 0 becomes 3, any other code is kept.

    Only the process's own entry point (`run`) replaces a dead standard output with None; a caller in the same process
    (a test, a library) gets its stream back exactly as it was.
    """
    out.flush()
    error = out.failure
    if error is None:
        return code
    if as_process:
        sys.stdout = cast(TextIO, None)   # the stream is unusable; None keeps the flush at exit from failing again
    if isinstance(error, BrokenPipeError):
        message = "the reader of standard output went away (broken pipe), so the output is cut short"
    else:
        message = f"could not write the report to standard output: {getattr(error, 'strerror', None) or error}"
    _say(f"{who}: {message}")
    return EXIT_NOT_DELIVERED if code == EXIT_OK and not isinstance(error, BrokenPipeError) else code


def _say(line: str) -> bool:
    """Write one line to stderr; False when stderr itself cannot be written (there is nowhere left to say it)."""
    if sys.stderr is None:   # print(file=None) would write to standard output, the stream that just failed
        return False
    try:
        print(line, file=sys.stderr)
    except (OSError, ValueError):
        return False
    return True


def _configure_logging(verbose: bool) -> None:
    """Send the `burnish` logger to stderr: debug with --verbose, otherwise the level in BURNISH_LOG_LEVEL (default WARNING)."""
    named = os.environ.get(LOG_LEVEL_ENV, "").strip().upper()
    if named and named not in _LEVELS:
        raise CannotRun(f"{LOG_LEVEL_ENV}={named!r} is not a level; use one of {', '.join(_LEVELS)}")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("burnish: %(levelname)s: %(message)s"))
    log.handlers[:] = [handler]
    log.propagate = False
    log.setLevel(logging.DEBUG if verbose else getattr(logging, named or "WARNING"))


def _require_something_to_read(command: str, path: Path) -> None:
    """Raise CannotRun unless `path` is a directory holding what `command` reads. A tree that was not read has no verdict."""
    if not path.exists():
        raise CannotRun(f"{path}: no such file or directory")
    if not path.is_dir():
        raise CannotRun(f"{path}: not a directory; give the folder that holds the code and the README")
    needs = _NEEDS[command]
    # A link that leads nowhere is an unreadable file, not an absent one. `check` meets a dangling `.py` link in its own
    # walk and says the same; the other commands skip links, so they are looked for here. Every command that reads or may
    # write the README refuses a dangling README link: a write through it would create its target, wherever that is.
    dangling = [] if command == "check" else broken_readme_links(path)
    if command not in ("check", "readme-critic"):
        dangling = dangling + list(broken_python_links(path))
    if dangling:
        raise OSError(errno.ENOENT, "broken symbolic link (its target cannot be reached)", str(dangling[0]))
    pythons = sum(1 for _ in (checkable_files(path) if command == "check" else python_files(path)))
    readme = find_readme(path)
    log.debug("%s: %d Python file(s), README %s", path, pythons, readme.name if readme else "absent")
    if readme is not None:
        readme.read_bytes()   # an unreadable README raises OSError here, which main reports as exit 2
    found = {"python": pythons > 0, "readme": readme is not None, "either": pythons > 0 or readme is not None}[needs]
    if not found:
        wanted = {"python": "Python files", "readme": "README", "either": "Python files or README"}[needs]
        raise CannotRun(f"{path}: found no {wanted} to read, so there is nothing to report")
    if command == "critic" and pythons == 0:   # a README alone: the critic's verdict compares it with code, and there is none
        raise CannotRun(f"{path}: found a README but no Python files to check it against, so there is nothing to check; "
                        "`readme-critic` reads a README on its own")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="burnish", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"burnish {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    # SUPPRESS keeps a flag given before the command from being reset by the command's own copy of it.
    common.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS,
                        help="log the debug trail to stderr (or set BURNISH_LOG_LEVEL)")
    parser.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS,
                        help="log the debug trail to stderr (or set BURNISH_LOG_LEVEL)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("check", "Python criteria a program can judge (PEP 8 items); exit 1 on any finding"),
        ("critic", "claims in the README and PROVENANCE against what the tree contains"),
        ("inspect", "what the tree declares about itself, as JSON"),
        ("readme", "print a README draft compiled from the tree (never writes)"),
        ("cns", "CNS seam recommendation (never modifies CNS)"),
    ):
        sub.add_parser(name, help=help_text, parents=[common]).add_argument("path", type=Path, nargs="?", default=Path("."))
    finish = sub.add_parser("finish", help="preview which files the finishing proposal would change (never writes)",
                            parents=[common])
    finish.add_argument("path", type=Path, nargs="?", default=Path("."))
    finish.add_argument("--scope", choices=["documentation", "code"], default=None,
                        help="documentation (default): the README only. code: tidy Python files too")
    readme_critic = sub.add_parser("readme-critic", help="a blunt review of the README against the README standard",
                                   parents=[common])
    readme_critic.add_argument("path", type=Path, nargs="?", default=Path("."))
    readme_critic.add_argument("--tier", choices=sorted(_TIERS), default="minimum",
                               help="the lowest tier that may still have a gap; exit 1 otherwise")
    sub.add_parser("criteria", help="list every criterion, its level and how implemented it is", parents=[common])
    sub.add_parser("languages", help="what is written and what is enforced, per language", parents=[common])
    for name in ("critic", "readme-critic"):
        sub.choices[name].add_argument("--collected", type=_count, default=None, metavar="N",
                                       help="the suite's collected test count (for example from `pytest --collect-only -q`), "
                                            "to check a count the README states; without it such a count is unverifiable")
    return parser


def _count(raw: str) -> int:
    """A non-negative whole number, for --collected."""
    if not raw.isdigit():
        raise argparse.ArgumentTypeError(f"{raw!r} is not a count (a whole number, zero or more)")
    return int(raw)


def _check(args: argparse.Namespace) -> int:
    findings = check_tree(args.path)
    log.info("checked %s: %d finding(s)", args.path, len(findings))
    for finding in findings:
        print(finding.render())
    counts = ", ".join(f"{k} {v}" for k, v in sorted(summarize(findings).items())) or "none"
    print(f"burnish check: {len(findings)} finding(s) ({counts})", file=sys.stderr)
    return EXIT_FINDINGS if findings else EXIT_OK


def _critic(args: argparse.Namespace) -> int:
    report = PoetryCritic().critique(args.path, collected=args.collected)
    print(report.as_markdown())
    return EXIT_OK if report.good_enough else EXIT_FINDINGS


def _readme_critic(args: argparse.Namespace) -> int:
    report = ReadmeCritic().critique(args.path)
    print(report.as_markdown())
    drifts = check_tree_claims(args.path) + check_test_claims(_readme_text(args.path), args.collected)
    if drifts:
        print("## Claims the tree contradicts or cannot back\n" + "\n".join(f"- {d.render()}" for d in drifts) + "\n")
    tier = _TIERS[args.tier]
    if report.failures or drifts:
        return EXIT_FINDINGS
    if tier is Tier.STRONG and report.gaps:
        return EXIT_FINDINGS
    if tier is Tier.OVER_THE_TOP and not report.over_the_top:
        return EXIT_FINDINGS
    return EXIT_OK


def _readme_text(root: Path) -> str:
    """The README's text, or an empty string when there is none (the command has already required one)."""
    path = find_readme(root)
    return path.read_text(encoding="utf-8", errors="replace") if path else ""


def _inspect(args: argparse.Namespace) -> int:
    narrative = inspect_tree(args.path)
    print(json.dumps({
        "name": narrative.name, "version": narrative.version,
        "cns_mentioned": narrative.cns_mentioned, "readme_exists": narrative.readme_exists,
        "modules": [{"path": m.path, "purpose": m.purpose, "classes": list(m.classes)} for m in narrative.modules],
    }, indent=2))
    return 0


def _readme(args: argparse.Namespace) -> int:
    narrative = inspect_tree(args.path)
    print(compile_readme(narrative, PoetryCritic().critique(args.path, narrative)))
    return 0


def _finish(args: argparse.Namespace) -> int:
    """List the files the finisher would change, using no measurements (a preview, not the real hand-off)."""
    seat = Burnish(scope=args.scope)
    proposal = seat.finish(args.path, "preview", Facts(suite=None, remaining=(), cycles=0))
    for edit in () if proposal is None else proposal.edits:
        print(edit.path)
    for note in seat.notes:
        print(f"burnish finish: note: {note}", file=sys.stderr)
    print(f"burnish finish: {0 if proposal is None else len(proposal.edits)} file(s) would change", file=sys.stderr)
    return 0


def _cns(args: argparse.Namespace) -> int:
    print(json.dumps(cns_to_dict(cns_analyse(args.path)), indent=2))
    return 0


def _criteria(_: argparse.Namespace) -> int:
    for c in CRITERIA:
        print(f"{c.id:16} {c.level.value:10} {c.state.value:16} {c.owner:10} {c.name}")
    return 0


def _languages(_: argparse.Namespace) -> int:
    print(describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
