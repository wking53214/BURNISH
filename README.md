# Burnish

*Formerly Streamline. Renamed in October 2026; the role is unchanged.*

What makes code beautiful, written down, checked, and applied to itself.

[![CI](https://github.com/wking53214/Burnish/actions/workflows/ci.yml/badge.svg)](https://github.com/wking53214/Burnish/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

[Install](#install) | [Usage](#usage) | [Architecture](#architecture) | [Languages](#languages) | [FAQ](#faq) | [Design](docs/DESIGN.md) | [Criteria](docs/CRITERIA.md) | [README standard](docs/README_STANDARD.md)

**Status:** version 0.2.0, alpha, maintained by one person. The Python checker, the README critic and the finisher work. The finisher tidies whitespace and keeps one generated, clearly marked facts section in the README; the rewrites for names, comments and guards are designed and **not built**; see [What it does not do](#what-it-does-not-do).

## What this is

Burnish is the home of the beautification criteria: naming as truth,
narrative documentation, architectural properties as comments, the rewriting
rules, best practices for Python, Rust and C++23, and the standard for a README
that is over the top. It also holds the tools that measure a tree against those
criteria and say, bluntly, where it falls short.

It is the finisher: it runs once, after the loop of Ghost Tools, Drafter, Warden and SWIZZLE has converged. It tidies the code and keeps one generated section in the README, with the critic's commentary. It still never writes a file itself. It returns a proposal, and [Warden](https://github.com/wking53214/Warden) applies it, which needs a named human and a green test suite first, and puts it back if the suite breaks or Ghost finds anything new.

## Why it exists

Beautifying code is easy to do badly. The original rules lived inside Warden,
mixed with the discipline of change, and in one edit the detailed text of the
principles and rules 1 to 6 was cut down to headings. The opinion about what
better code is deserved its own repository, with its full text restored, so it
could be judged, improved and applied to itself.

## Install

```bash
pip install git+https://github.com/wking53214/Burnish.git
```

This also installs [Warden](https://github.com/wking53214/Warden), which
Burnish plugs into. Python 3.11 or newer. No other dependencies.

To work on it:

```bash
git clone https://github.com/wking53214/Burnish.git
cd Burnish
pip install -e ".[dev]"
pytest
```

### Bumping the Warden pin

This package depends on one exact Warden commit (see `dependencies` in `pyproject.toml`), so a change on
Warden's `main` cannot break it without anyone noticing. To move to a newer Warden:

1. Pick the Warden commit (or `vX.Y.Z` tag) you want.
2. Put it after the `@` in the `warden @ git+...` line of `pyproject.toml`.
3. Run `pip install -e ".[dev]"` and `pytest`. The tests check that the pin is a tag or a full commit and that
   this package's `requires_contract` matches the installed Warden's `CONTRACT`.
4. Open a pull request. CI runs the same checks.

## Usage

Ask for a blunt review of any repository's README:

```bash
burnish readme-critic path/to/repo
```

```text
# README critic: README.md

This README fails the minimum: 5 thing(s) a reader needs are missing or broken. It is not ready to be someone's first impression.

## Failures (minimum not met)
- [RM-ONELINER] It never says what the project is in one plain sentence. (the first sentence is 446 characters; the limit is 120)
- [RM-INSTALL] A reader cannot get this running. (no section matching /install|setup|getting started/)
- [RM-LICENSE] A reader cannot tell whether they may use it. (no License section)
- [RM-CONTRIB] Nobody can tell if help is wanted. (no Contributing section)
```

That output is real: it is what the critic said about a sibling repository on
the day it was written. The exit code is 1 when the README is below the tier
asked for (`--tier minimum`, `strong` or `over-the-top`).

Check Python code against the rules a program can judge:

```bash
burnish check path/to/repo
```

```text
risky.py:4: PY-TYPE: `risky` has no annotation for: path, return
risky.py:8: PY-EXC: bare `except:` catches everything, including KeyboardInterrupt; name the exceptions
risky.py:8: PY-SWALLOW: the handler only passes, so a failure looks like success; handle it or let it rise
burnish check: 3 finding(s) (PY-EXC 1, PY-SWALLOW 1, PY-TYPE 1)
```

That output is also real, from a four-line demo file with a bare `except` that
passes. The exit code is 1 when anything is found.

The other commands:

| Command | What it does |
|---------|--------------|
| `burnish critic PATH` | Reads the README and modules against what the tree declares. Exit 1 on "This isn't good enough yet." |
| `burnish inspect PATH` | What the tree declares about itself, as JSON |
| `burnish readme PATH` | Prints a README draft compiled from the tree. Never writes |
| `burnish finish PATH` | Lists the files the finishing proposal would change. Never writes |
| `burnish cns PATH` | A recommendation about a repository's CNS seam. Never modifies CNS |
| `burnish criteria` | Every criterion, its level, and how implemented it is |
| `burnish languages` | What is written down and what is enforced, per language |

To finish a repository, hand Burnish to Warden as the finisher. Nothing
is written without `--authorize`:

```bash
warden tagteam path/to/repo --drafter drafter.seat:Drafter --finisher burnish.finisher:Burnish --ghost-root ../ghost_tools --swizzle-root ../SWIZZLE
```

### What the finisher does to a README

It writes only between two comment lines of its own, which Markdown does not
show. Everything else in the README is yours and is never touched, even a
section you headed "Claims vs reality".

```text
<!-- burnish:begin claims-vs-reality -->
## Measured facts (generated)
...
<!-- burnish:end -->
```

Inside that section it says what Warden measured, what was not measured, and
where a number you wrote does not match (for example "The README says a count of
999; the measured suite has 5 passing. These disagree."). It judges only claims
about this project's own suite ("all tests pass", "30/30 passing", a bare
full-coverage figure). It does not judge a change ("added 5 tests"), a history ("before the
fix, 10 tests failed"), another thing's count (a version, a file, a table row, a
named subject) or a denial ("we make no claim of full coverage"). Counts it skips
because they belong to something else are only counted, never quoted, so Ghost
Tools does not read the report as a new claim. Skipped tests are not failures: a
claim of 30 passing over 28 passed and 2 skipped agrees, with the skips named,
unless the README says nothing is skipped. It reports; it never rewrites your
sentences. Run it again on its own result and it proposes nothing. A
reStructuredText or plain-text README is not changed at all; Burnish only says
so in its notes. If a repository has no README, it writes a README.md once.

Markers shown in a fenced or indented code block, or inside an HTML comment, are
examples and are ignored. Everything you wrote is kept byte for byte, including
trailing blank lines, mixed line endings and a missing final newline; the block
is added after it. A README that ends inside an HTML comment that was never
closed gets a closing `-->` line first, so the block is not swallowed.

### What the finisher will not touch, and when it tidies code

It never proposes a change to a test file, test setting, CI file or Ghost file
(`test_*.py`, `*_test.py`, `tests/`, `testing/`, `conftest.py`, `noxfile.py`,
`tox.ini`, `pytest.ini`, `setup.cfg`, `pyproject.toml`, `.github/`, `.ghost_*`):
the Judge turns away a run that changes one, even by whitespace, and Warden then
puts everything back. It also skips vendored and generated code, using the same
list Warden uses: `vendor`, `third_party`, `extern`, `external`, `generated`,
`gen`, `build`, `dist`, `node_modules`, and any file whose first ten lines say
"do not edit", "generated by", "auto-generated", "autogenerated" or
"@generated". The list is copied from Warden's guard, not imported, so a change
there needs a change in `burnish/files.py`.

A finish that mixes code with the README is rejected whole under Warden's
default `documentation` grant. Burnish does not know the grant, so by default it
proposes only the README. To include tidied Python files, say the grant covers
code: `BURNISH_SCOPE=code`, `Burnish(scope="code")` or `burnish finish PATH
--scope code`. After a finish, `docs_edits` and `code_edits` hold the two kinds
of edit, and `finish_docs` and `finish_code` return one proposal each.

## Architecture

```text
criteria.py          the rules, as data
   │
   ├── checks.py          Python rules a program can judge
   ├── readme_critic.py   README rules, in three tiers
   └── critic.py          the critic's commentary on measured facts
                              │
narrative.py  reads the tree  │
files.py      which files are the target's own; finds the README
beautify.py   tidies Python source, behavior-preserving, keeps line endings
marked.py     the markers around the only README text Burnish may write
claims.py     the README's own test counts, checked against the measured suite
measured.py   reads Warden's facts; a suite that did not run is not a measurement
textsafe.py   makes text from other tools safe to print into a README
readme.py     compiles and finalizes the README
finisher.py   the one proposal Warden asks for, once, after the loop
```

Invariants, each enforced by a test:

- No Burnish module writes or deletes a file.
- No Burnish module counts tests or imports another role (Drafter, Ghost Tools, SWIZZLE, ASSAY). What it says about the suite or about defects, it quotes from the facts Warden hands it.
- Nothing is called `IMPLEMENTED` unless Burnish enforces it, and nothing is called enforced for Rust or C++23.
- Burnish passes its own Python checks and its own README critic at the over-the-top tier.
- The criteria table and the documents cannot disagree.

The reasoning, the analogy behind the design, and what was rejected are in
[docs/DESIGN.md](docs/DESIGN.md).

## Languages

| Language | Authority | Burnish checks it | Exemplar | Enforced in CI by |
|----------|-----------|----------------------|----------|-------------------|
| Python | [PEP 8](https://peps.python.org/pep-0008/) | **Yes**, eight rules | [exemplars/python](exemplars/python) | `burnish check`, `pytest` |
| Rust | [API Guidelines](https://rust-lang.github.io/api-guidelines/) | **No**, written down only | [exemplars/rust](exemplars/rust) | `cargo fmt`, `clippy -D warnings`, `cargo test` |
| C++23 | [Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) | **No**, written down only | [exemplars/cpp23](exemplars/cpp23) | `g++ -std=c++23 -Werror`, `ctest` |

Each exemplar is the same small program, durable defect IDs (rule `R9`),
written to its language's rules. All three read one file of test vectors,
[exemplars/vectors.txt](exemplars/vectors.txt), so they cannot quietly disagree.
Guides: [Python](docs/languages/python.md), [Rust](docs/languages/rust.md),
[C++23](docs/languages/cpp23.md). The craft practices that lift code past
correct are in [docs/CRAFT.md](docs/CRAFT.md).

## The README standard

Three tiers, from the sources listed in [docs/README_STANDARD.md](docs/README_STANDARD.md)
and [docs/RESEARCH.md](docs/RESEARCH.md): the **minimum** a reader needs, what makes
a README **strong**, and what makes it **over the top**. The over-the-top tier is
a synthesis, and the standard says so. This README is held to it.

## FAQ

**Does it give a beauty score?** No. A number hides which rule failed. Every
report is a list of named rules.

**Can it fix my code?** Not by itself. Fixing is the Drafter's job, inside the loop. Burnish runs once, after the loop, and proposes a tidy and the final README. Warden, with a human grant and a green suite, decides. Today the tidy removes trailing whitespace and nothing else.

**Why does it check Python but not Rust or C++?** Because only Python has a
checker. Rust and C++23 have written criteria and a working exemplar, and the
language's own tools enforce the exemplar in CI. `burnish languages` says so.

**Why is the critic so harsh?** Because a critic that praises is a brochure. The
README critic is allowed, and required, to say a README is not good.

## What it does not do

WHAT IT DOES NOT OWN:

- Writing to a repository. That is Warden's, behind a human grant.
- The test gate, the SWIZZLE proof gate and the audit file. Also Warden's.
- Forensic detection of long functions, dead code and duplicates, and counting tests. That is ghost_tools.
- Proposing fixes inside the loop. That is Drafter.
- Renaming, narrative comments, inline architectural comments, guards and function splits. They are designed (`PA`, `PB`, `PC`, `R1` to `R4`) and have no rewriter.
- Checking Rust or C++23 code.
- Judging whether prose is clear or an image is good, fetching URLs, or telling a dead external link.
- Scoring anything.

## Alternatives

Formatters and linters such as ruff, black, clippy and clang-tidy enforce
style on one language and should be used alongside this. READMEs have templates
and spec checkers such as Standard Readme. Burnish differs in two ways: it
keeps the criteria, the languages and the README standard in one place that
checks itself, and it separates the opinion about better code from the
authority to change it.

## Evidence

CI runs the Python tests on 3.11 and 3.12, runs Burnish on itself, builds the
Rust exemplar with clippy and rustfmt, and builds the C++23 exemplar with GCC and
warnings as errors.

148 tests exist in this tree. They are Python `test_*` functions; the
Rust and C++ exemplars have their own checks under `ctest` and `cargo test`.

## Claims versus reality

Here is what the artifact says it is: the home of the beautification criteria,
with tools that measure code against them and say so bluntly.

Here is what we can establish: the checker, the README critic and the critic
of claims run, are tested, and pass on this tree. The three exemplars build and
agree on the same vectors.

Here is where those disagree: the criteria describe far more than is enforced.
Of the Python criteria, eight are checked. Of the Rust and C++23 criteria, none are
checked by Burnish. Most of the craft practices need a person. Counting the
whole table, the share marked `IMPLEMENTED` is small, and `burnish criteria`
prints exactly which. Clang 18 with libstdc++ 13 cannot build the C++ exemplar;
only GCC was verified. The research behind the guides has gaps, listed in
[docs/RESEARCH.md](docs/RESEARCH.md).

What works, measured by the tests in this tree: running the finisher on its
own output proposes nothing (checked five times over, from a README that was
missing, old-format and hand-written); a hand-written section is never touched;
a test run that failed to start is reported as not measured; README numbers that
disagree with the measured suite are named; text that Ghost Tools supplies
cannot forge a heading or close the generated section; CRLF files, byte order
marks and files that are not UTF-8 are handled without a crash and without
changing line endings; environments, vendored code and generated files are not
tidied.

Known defects. The test-count check looks for fixed phrasings such as "999
tests pass" or "5/5 passed" and misses other wording, for example "ninety
tests". Python files that start with a byte order mark are skipped rather than
tidied, because Warden's own syntax check cannot read them. A README that ends
inside an unclosed code block is left alone. A README with no file extension, or
a `.rst` or `.txt` one, gets no generated section. The tidy still reaches test
files, with whitespace-only changes that Warden allows because the syntax tree
is identical.

## Roadmap

Outstanding, in the order a person would likely want them:

1. A first rewrite for names or comments in the finisher, behind Warden's gate.
2. Read the parts of the C++ Core Guidelines the first pass missed, and add their criteria.
3. A Rust checker, if Clippy's lints are not enough.
4. Run Warden's loop with Drafter and Burnish in their seats on a real repository and record it in Warden's registry.

## Support

Open an [issue](https://github.com/wking53214/Burnish/issues) for questions
or bugs.

## Contributing

Issues and pull requests are welcome. Run `pytest` and `burnish check .`
first; both must pass, and the README critic must still say the README is over
the top. A change to a criterion changes `burnish/criteria.py` and the page
that describes it in the same pull request, or the docs-in-sync test fails.

## Design analogy

Burnish is a style editor beside a safety inspector. The editor knows what
good writing looks like and marks it up; the inspector decides whether the
building may be changed at all and checks it afterwards. In operational terms,
Burnish reviews and proposes and Warden authorizes, gates and records. The
full table of vibecode, plain language and operational terms is in
[docs/DESIGN.md](docs/DESIGN.md).

## License

Apache-2.0. Copyright 2026 William N. King. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
