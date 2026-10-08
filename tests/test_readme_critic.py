"""The README critic is blunt, sorted by tier, and never gives a number."""

from pathlib import Path

from burnish.cli import main
from burnish.readme_critic import RULES, ReadmeCritic, Tier

OVER_THE_TOP = '''# demo

A tiny tool that counts things so you do not have to.

[![CI](https://github.com/x/demo/actions/workflows/ci.yml/badge.svg)](https://github.com/x/demo/actions)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

[Install](#install) | [Usage](#usage) | [Architecture](#architecture) | [FAQ](#faq) | [Docs](docs/DESIGN.md)

**Status:** stable, maintained.

## Install

```bash
pip install demo
```

## Usage

```bash
demo count notes.txt
```

```text
3 lines
```

See [examples/basic.py](examples/basic.py).

## Architecture

```text
input -> counter -> report
```

Invariant: a count is never negative. Design decisions are in [the design notes](docs/DESIGN.md).

## What it does not do

It does not parse binary files.

## Alternatives

Compared with `wc`, demo explains its answer.

## FAQ

Why not `wc`? See above.

## Roadmap

Next: streaming input.

## Verified by

12 tests exist and run in CI.

## Support

Open an issue for questions.

## Contributing

Pull requests are welcome. Ask questions in an issue.

## License

Apache-2.0, William N. King.
'''


def _repo(tmp_path: Path, readme: str) -> Path:
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "DESIGN.md").write_text("# design\n", encoding="utf-8")
    (tmp_path / "examples").mkdir(exist_ok=True)
    (tmp_path / "examples" / "basic.py").write_text("print(3)\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("Apache\n", encoding="utf-8")
    return tmp_path


def test_a_missing_readme_is_a_failure(tmp_path: Path):
    report = ReadmeCritic().critique(tmp_path)
    assert not report.meets_minimum and "no front door" in report.verdict


def test_a_bare_readme_fails_the_minimum_and_says_what_is_missing(tmp_path: Path):
    report = ReadmeCritic().critique(_repo(tmp_path, "# demo\n\nA thing.\n"))
    failed = {gap.rule.id for gap in report.failures}
    assert {"RM-INSTALL", "RM-USAGE", "RM-LICENSE", "RM-CONTRIB", "RM-LIMITS"} <= failed
    assert "fails the minimum" in report.verdict
    assert "A reader cannot get this running." in report.as_markdown()


def test_a_complete_readme_is_over_the_top(tmp_path: Path):
    report = ReadmeCritic().critique(_repo(tmp_path, OVER_THE_TOP))
    assert report.over_the_top, report.as_markdown()
    assert report.verdict.startswith("Over the top")


def test_a_broken_relative_link_fails(tmp_path: Path):
    repo = _repo(tmp_path, OVER_THE_TOP.replace("docs/DESIGN.md", "docs/NOPE.md"))
    report = ReadmeCritic().critique(repo)
    assert "RM-LINKS" in {g.rule.id for g in report.failures}


def test_a_license_section_must_name_a_license(tmp_path: Path):
    repo = _repo(tmp_path, OVER_THE_TOP.replace("Apache-2.0, William N. King.", "See the repository."))
    assert "RM-LICENSE" in {g.rule.id for g in ReadmeCritic().critique(repo).failures}


def test_fenced_code_is_not_mistaken_for_headings(tmp_path: Path):
    readme = OVER_THE_TOP.replace("pip install demo", "# not a heading\npip install demo")
    report = ReadmeCritic().critique(_repo(tmp_path, readme))
    assert "RM-INSTALL" not in {g.rule.id for g in report.failures}


def test_every_rule_belongs_to_a_tier_and_has_a_source():
    assert {r.tier for r in RULES} == set(Tier)
    assert all(r.source and r.blunt and r.name for r in RULES)
    assert len({r.id for r in RULES}) == len(RULES)


def test_cli_exit_codes_follow_the_requested_tier(tmp_path: Path):
    bare = _repo_in(tmp_path / "bare", "# demo\n\nA thing.\n")
    good = _repo_in(tmp_path / "good", OVER_THE_TOP)
    assert main(["readme-critic", str(bare)]) == 1
    assert main(["readme-critic", str(good), "--tier", "over-the-top"]) == 0


def _repo_in(path: Path, readme: str) -> Path:
    path.mkdir()
    return _repo(path, readme)
