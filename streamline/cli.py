"""streamline: read a tree, say what is wrong with it, plainly.

Every command here only reads. Changing a repository is Elegant's job and
needs a human grant; `elegant tagteam --finisher streamline.finisher:Streamline`
is how Streamline's one-time finishing proposal reaches a file.

EXIT CODES
  0  nothing to report at the level asked for
  1  findings (or a README below the requested tier)
  2  could not run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .checks import check_tree, summarize
from .cns_boundary import analyse as cns_analyse
from .cns_boundary import to_dict as cns_to_dict
from elegant.roles import Facts

from .criteria import CRITERIA
from .critic import PoetryCritic
from .finisher import Streamline
from .languages import describe
from .narrative import inspect_tree
from .readme import compile_readme
from .readme_critic import ReadmeCritic, Tier

_TIERS = {"minimum": Tier.MINIMUM, "strong": Tier.STRONG, "over-the-top": Tier.OVER_THE_TOP}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run one command and return its exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    handlers = {
        "check": _check, "critic": _critic, "readme-critic": _readme_critic, "inspect": _inspect,
        "readme": _readme, "finish": _finish, "cns": _cns, "criteria": _criteria, "languages": _languages,
    }
    return handlers[args.command](args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="streamline", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"streamline {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("check", "Python criteria a program can judge (PEP 8 items); exit 1 on any finding"),
        ("critic", "claims in the README and PROVENANCE against what the tree contains"),
        ("inspect", "what the tree declares about itself, as JSON"),
        ("readme", "print a README draft compiled from the tree (never writes)"),
        ("finish", "preview which files the finishing proposal would change (never writes)"),
        ("cns", "CNS seam recommendation (never modifies CNS)"),
    ):
        sub.add_parser(name, help=help_text).add_argument("path", type=Path, nargs="?", default=Path("."))
    readme_critic = sub.add_parser("readme-critic", help="a blunt review of the README against the README standard")
    readme_critic.add_argument("path", type=Path, nargs="?", default=Path("."))
    readme_critic.add_argument("--tier", choices=sorted(_TIERS), default="minimum",
                               help="the lowest tier that may still have a gap; exit 1 otherwise")
    sub.add_parser("criteria", help="list every criterion, its level and how implemented it is")
    sub.add_parser("languages", help="what is written and what is enforced, per language")
    return parser


def _check(args: argparse.Namespace) -> int:
    findings = check_tree(args.path)
    for finding in findings:
        print(finding.render())
    counts = ", ".join(f"{k} {v}" for k, v in sorted(summarize(findings).items())) or "none"
    print(f"streamline check: {len(findings)} finding(s) ({counts})", file=sys.stderr)
    return 1 if findings else 0


def _critic(args: argparse.Namespace) -> int:
    report = PoetryCritic().critique(args.path)
    print(report.as_markdown())
    return 0 if report.good_enough else 1


def _readme_critic(args: argparse.Namespace) -> int:
    report = ReadmeCritic().critique(args.path)
    print(report.as_markdown())
    tier = _TIERS[args.tier]
    if report.failures:
        return 1
    if tier is Tier.STRONG and report.gaps:
        return 1
    if tier is Tier.OVER_THE_TOP and not report.over_the_top:
        return 1
    return 0


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
    proposal = Streamline().finish(args.path, "preview", Facts(suite=None, remaining=(), cycles=0))
    for edit in () if proposal is None else proposal.edits:
        print(edit.path)
    print(f"streamline finish: {0 if proposal is None else len(proposal.edits)} file(s) would change", file=sys.stderr)
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
    raise SystemExit(main())
