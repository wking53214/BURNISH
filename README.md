# Burnish

*Formerly Streamline. Renamed in October 2026; the role is unchanged.*

What makes code beautiful, written down, checked, and applied to itself.

[![CI](https://github.com/wking53214/Burnish/actions/workflows/ci.yml/badge.svg)](https://github.com/wking53214/Burnish/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

[Install](#install) | [Usage](#usage) | [Architecture](#architecture) | [Languages](#languages) | [FAQ](#faq) | [Design](docs/DESIGN.md) | [Criteria](docs/CRITERIA.md) | [README standard](docs/README_STANDARD.md)

**Status:** version 0.3.9, alpha, maintained by one person. The Python checker, the README critic and the finisher work. The finisher tidies whitespace and keeps one generated, clearly marked facts section in the README; the rewrites for names, comments and guards are designed and **not built**; see [What it does not do](#what-it-does-not-do).

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

This also installs the two things Burnish is built on, each pinned to one exact commit that
`pyproject.toml` records (see `dependencies` there, and [Bumping the Warden pin](#bumping-the-warden-pin)):
[Warden](https://github.com/wking53214/Warden), which Burnish plugs into, and
[CNS](https://github.com/wking53214/CNS), the shared data shapes that both import. Python 3.11 or newer.
Those two are the only runtime dependencies. If you install Warden separately, use the commit `pyproject.toml` names.

To work on it:

```bash
git clone https://github.com/wking53214/Burnish.git
cd Burnish
pip install -e ".[dev]"
pytest
ruff check .
mypy
```

### Bumping the Warden pin

This package depends on one exact Warden commit (see `dependencies` in `pyproject.toml`), so a change on
Warden's `main` cannot break it without anyone noticing. To move to a newer Warden:

1. Pick the Warden commit you want, and note the release it belongs to.
2. Put the full 40-character commit after the `@` in the `warden @ git+...` line of `pyproject.toml`, and the release it
   corresponds to in the comment on that line. The CNS line is different: it is pinned by its release tag
   (`@v1.9.0`), the spelling every repository in the circuit uses, with the commit the tag peels to in the comment.
3. Run `pip install -e ".[dev]"` and `pytest`. The tests check that Warden is pinned to a full commit, that CNS is
   pinned by tag, and that this package's `requires_contract` matches the installed Warden's `CONTRACT`.
4. Open a pull request. CI runs the same checks.

### Bumping the toolchain pins

The Rust and C++23 jobs are pinned so that a new stable release cannot turn CI red without anyone choosing it:

- **Rust.** `exemplars/rust/rust-toolchain.toml` names one exact release (`channel = "1.99.0"`, with clippy and rustfmt).
  The job installs it, prints `rustc`, `cargo` and `clippy` versions, and fails if `rustc` is not that release. To move,
  change `channel`, then run `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings` and
  `cargo test --locked` in `exemplars/rust`, fix any new lint the release brings, and open a pull request.
  `rust-version` in `exemplars/rust/Cargo.toml` is the declared minimum the crate says it supports; CI does not build with
  it, so it is not claimed to be tested. Keep it at or below `channel`.
- **C++23.** The job runs on the named image `ubuntu-24.04`, installs `g++-${GXX_MAJOR}` and `cmake` from apt, prints
  both versions, and fails unless the g++ major version is `GXX_MAJOR` and the cmake major version is `CMAKE_MAJOR`
  (both set in the job's `env:` in `.github/workflows/ci.yml`). Exact apt package versions are not pinned because the
  archive drops old ones. The cmake release is whatever the image provides (CI runs have seen both 3.28.3 and 3.31.6),
  so only its major version is asserted; the warnings come from g++. To move to another compiler, change `GXX_MAJOR`
  together with the image, then run the three `cmake` and `ctest` steps from that job.
- **Runner image.** Moving either job to a newer Ubuntu image is a bump of the same kind: change `runs-on`, then the values above.

## Usage

Ask for a blunt review of any repository's README:

```bash
burnish readme-critic path/to/repo
```

```text
# README critic: README.md

Over the top. Every rule holds. Re-run it after every change; it will not stay that way by itself.

## What holds
- RM-TITLE Title
- RM-ONELINER One-line description
- RM-INSTALL Install, with a command
- RM-USAGE Usage, with a code block
- RM-LICENSE License, named
- RM-LINKS No broken relative links
- RM-SIZE Under GitHub's size limit
- RM-CONTRIB Contributing, with a stance
- RM-LIMITS Says what it will not do
- RM-STATUS Project status
- RM-SUPPORT Where to get help
- RM-TOC Navigation for a long README
- RM-FENCES Code blocks name their language
- RM-EXAMPLES Runnable examples
- OT-QUICKLINKS A way in within one screen
- OT-VISUAL A picture of the thing
- OT-DEMO A demo with its output
- OT-BADGES Badges that carry information
- OT-ARCH Architecture with invariants
- OT-EVIDENCE Claims come with their evidence
- OT-FAQ A FAQ
- OT-ALTERNATIVES Compared with the alternatives
- OT-ROADMAP A roadmap
- OT-DECISIONS Design decisions linked
```

That output is real: it is what `burnish readme-critic .` prints for this repository's own README, and a test fails
if this block stops matching the command. A README with gaps gets a failures section instead, one line per broken rule.
The exit code is 1 when the README is below the tier
asked for (`--tier minimum`, `strong` or `over-the-top`), or when it states a pin, a dependency list or a test count
that the tree contradicts or cannot back.

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
| `burnish critic PATH` | Checks claims in the README and PROVENANCE against what the tree contains: test counts, pins, dependency lists. Exit 1 on "This isn't good enough yet." |
| `burnish inspect PATH` | What the tree declares about itself, as JSON |
| `burnish readme PATH` | Prints a README draft compiled from the tree. Never writes |
| `burnish finish PATH` | Lists the files the finishing proposal would change. Never writes |
| `burnish cns PATH` | A recommendation about a repository's CNS seam. Never modifies CNS |
| `burnish criteria` | Every criterion, its level, and how implemented it is |
| `burnish languages` | What is written down and what is enforced, per language |

The README critic has its own command, `burnish readme-critic PATH [--tier minimum|strong|over-the-top]`, shown above.

### What the critics catch that a reader would

Three kinds of sentence are checked against the tree, not just against the README's own shape:

- **A pin.** "Pinned to tag X" is compared with the ref and the release comment on that dependency's line in
  `pyproject.toml`. The README should point at `pyproject.toml` rather than restate the pin.
- **A dependency list.** "No other dependencies" is compared with the dependencies declared there and the third-party
  modules the code imports.
- **A test count.** Burnish counts no tests, so a number the README gives for its suite is reported as unverifiable
  unless a count is supplied: `--collected N` takes the total from `pytest --collect-only -q`, and when the
  finisher runs under Warden the measured suite is used instead. A count that cannot be true is reported either way.
  The simplest honest README states no such number.

### Exit codes and logging

Every command that takes a path reads a folder, and a folder it cannot read has no verdict: a missing path, a path
that is not a folder, a folder with nothing to read (no Python files, or for `readme-critic` no README) and an
unreadable file all exit 2 with the reason on stderr, never "0 findings". A broken symbolic link with a Python name
(`.py`) is an unreadable file, and every command that reads Python says "broken symbolic link" for it. So is a broken link with a README name, for every
command that reads or may write the README (all but `check`), instead of "found no README": a write through it would create its
target, wherever that is. `finish` also never proposes an edit to a file that is a symbolic link or lies under one, whether the
link is broken or not; it says so in its notes.

A folder with Python but no README is not a failure for `critic`, `readme`, `inspect`, `cns` or `finish`; only
`readme-critic` needs a README to judge. The missing README is itself reported or supplied: `critic` lists "There is no
README" among what is still ugly, `inspect` says `readme_exists` is false, `readme` prints a compiled draft, and `finish` lists
`README.md` as a file it would create. Each exits 0, and a test keeps that so.

| Code | Meaning |
|------|---------|
| 0 | Nothing to report at the level asked for. |
| 1 | Findings, or a README below the requested tier, or a README claim the tree contradicts. |
| 2 | Could not run: bad usage, a path that is missing or unreadable, or a path with nothing to check. |
| 3 | The report could not be delivered (standard output closed or full) and the check itself would have exited 0. |

A report that cannot be delivered is not a silent success. If the reader of a pipe went away (`burnish critic . | head -3`),
the output is cut short, one line on stderr says so, and the exit code stays the one the check earned: the reader chose to stop,
and the check still ran to the end. Any other failure to write standard output (it is closed, or the device is full) also gets
one line on stderr saying why. An earned 1 or 2 stays as it is; an earned 0 becomes 3, because exit 0 would claim a report
that nobody received. No command ends in a traceback for this, including `--version` and `--help`, and the exit status 120
that Python gives a failed flush at exit is never what you see. The line goes to stderr; if stderr cannot be written either,
the exit code is all there is.

Messages go to stderr through Python's `logging`. `--verbose` (or `-v`, before or after the command) shows the debug trail,
and `BURNISH_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`) sets the level when `--verbose` is not given.
A test keeps this table equal to the code.

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
default `documentation` grant. Burnish cannot see the grant itself, so by default it
proposes only the README. Warden (0.11.0 or newer) sets Burnish's `scope` to the
grant's scope before the finish, so a run with `--scope code` gets the tidied
Python files too. Outside Warden, say it yourself: `BURNISH_SCOPE=code`,
`Burnish(scope="code")` or `burnish finish PATH --scope code`. After a finish,
`docs_edits` and `code_edits` hold the two kinds of edit, and `finish_docs` and
`finish_code` return one proposal each.

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
cns_boundary.py  the read-only CNS seam recommendation (`burnish cns`)
languages.py  what is written and what is enforced, per language (`burnish languages`)
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
| C++23 | [Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) | **No**, written down only | [exemplars/cpp23](exemplars/cpp23) | `cmake` with `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror` (C++23), `ctest` |

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

CI runs the Python tests on 3.11, 3.12 and 3.13, runs `ruff` and `mypy` as gates, runs Burnish on itself, builds the
Rust exemplar with clippy and rustfmt, and builds the C++23 exemplar with GCC and
warnings as errors. Both toolchains are pinned and their versions are asserted in the job.

The suite passes against the Warden commit that `pyproject.toml` pins. This README states no test count on purpose: a number
here goes stale the first time a test is added, and Burnish's own critic reports an unbacked count as a defect.
`pytest --collect-only -q` gives the real figure.

The three Warden-loop tests (`test_finisher.py::test_through_warden_the_code_is_tidied_and_the_readme_keeps_the_authors_words`, `test_finisher.py::test_nothing_to_finish_means_no_proposal` and `test_stable_and_careful.py::test_through_warden_a_second_finish_proposes_nothing`) now follow Warden's held-result rule: a finish that is not a full `ACCEPT` is put back and held, and the test keeps it with a grant before checking the result. Their earlier form expected a change to stand after `ACCEPT_UNVERIFIED`, which Warden no longer allows. No tests are skipped or marked expected-to-fail. The Rust and C++ exemplars have their own checks under `cargo test` and `ctest`.

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
changing line endings; environments, vendored code, generated files and test material (`fixtures`,
`specimens`, `testdata`, `golden`, `snapshots`, `corpus` folders) are not tidied:
when the circuit ran on ASSAY, its own answer key, the tidy reformatted thirteen
specimens and only the suite's recorded hashes caught it.

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
4. Run Warden's loop with Drafter and Burnish in their seats on a real repository and record it in Warden's registry. The loop has run with every seat live on a scratch repository (2026-10-14, `warden tagteam --stack`; under a `code` grant Burnish's tidy and README section were both applied and the run ended `ACCEPT`), and that run is in Warden's `docs/REGISTRY.json`; a real repository is still to do.

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
