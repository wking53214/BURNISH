# Burnish

*Formerly Streamline. Renamed in October 2026; the role is unchanged.*

What makes code beautiful, written down, checked, and applied to itself.

[![CI](https://github.com/wking53214/Burnish/actions/workflows/ci.yml/badge.svg)](https://github.com/wking53214/Burnish/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

[Install](#install) | [Usage](#usage) | [What works](#what-works-and-what-shows-it) | [What does not](#what-does-not-work-or-is-not-proven) | [Known defects](#known-defects-open) | [Architecture](#architecture) | [Languages](#languages) | [FAQ](#faq) | [Design](docs/DESIGN.md) | [Criteria](docs/CRITERIA.md) | [README standard](docs/README_STANDARD.md)

**Status:** version 0.3.19, alpha, maintained by one person. The Python checker, the README critic, the claims critic and the finisher are tested (see [What works](#what-works-and-what-shows-it)). The finisher tidies trailing whitespace and keeps one generated, clearly marked facts section in the README. The rewrites for names, comments and guards are designed and **not built**; see [What does not work](#what-does-not-work-or-is-not-proven).

## What this is

Burnish is a written set of rules for what makes Python, Rust and C++23 code and a README better, plus the tools that measure a tree against the rules a program can judge: eight Python checks, a README critic with a rule list, and a critic that compares what a README says with what the tree contains. It can also act as the finisher in the Warden loop (an explicit `--finisher`; it is released from the circuit, see the status note below): it runs once, after the loop has converged, and proposes a whitespace tidy and one generated section in the README. It never writes a file itself; it returns a proposal, and [Warden](https://github.com/wking53214/Warden) applies it or puts everything back.

**Status: released from the circuit (2026-10-29).** Burnish was the finisher seat in the Horsemen circuit, and the owner has released it from the circuit. Released means removed from the circuit and nothing else: the code, the tests, the history and the CI are intact, and Burnish still works on its own as described below. The reason, with the evidence: across the thirteen self-hosting runs of 2026-10-22 and 2026-10-23, the sections the finisher generated were the only change the circuit kept, and the two FINISH_REJECTED results the finisher's change caused (SWIZZLE and JUDGE, first run) were caused by that text. The record is in the CNS repository under `docs/evidence/selfhosting-records-2026-10-23/`. What remains usable on its own: `burnish check`, `burnish critic` and `burnish readme-critic` run standalone on any tree. In the circuit, the pinned manifest in the CNS repository omits Burnish, so the circuit does not install it. The explicit flow `--finisher burnish.finisher:Burnish` with a bare `--stack` still works, and a bare `--stack` still needs all six checkouts (drafter and burnish included); only a pinned `--stack-manifest` that omits Burnish, with a folder that lacks it, runs without it. Burnish is free to be reborn elsewhere; that is the owner's intent, not a plan or a promise.

## Why it exists

On 2026-10-08 the critic, the narrative reader and the README compiler were removed from Warden's package (Warden commit `81cd431`, when Warden was still called Elegant), so that Warden would only govern change and the opinion about what better code is would live in its own repository. This repository started the same day under the name Streamline. The opinion could then be judged, improved and applied to itself.

## Install

```bash
pip install git+https://github.com/wking53214/Burnish.git   # installs main, which is 0.3.10 until the owner fast-forwards it; this branch is 0.3.19, so use a checkout of it for the current code
```

This also installs the two things Burnish is built on, each pinned in `pyproject.toml` (see `dependencies` there, and [Bumping the Warden pin](#bumping-the-warden-pin)):
[Warden](https://github.com/wking53214/Warden), which Burnish plugs into, and
[CNS](https://github.com/wking53214/CNS), the shared data shapes that both import. Python 3.11 or newer; CI runs 3.11, 3.12 and 3.13 on Linux.
Those two are the only runtime dependencies. If you install Warden separately, use the commit `pyproject.toml` names.

Do not install any of these by bare name. Burnish is not on PyPI (on 2026-10-22 there was no project of that name there), and `warden` and `cns` on PyPI are other people's projects. Use the git URL above or a checkout.

To work on it:

```bash
git clone https://github.com/wking53214/Burnish.git
cd Burnish
pip install -e ".[dev]"
pytest
ruff check .
mypy
```

CNS has a migration note. The pin moved from `v1.9.0` to `v2.0.0` in Burnish 0.3.11. Burnish imports `cns.seat`, `cns.suite`, `cns.epistemic` and `cns.defect`, and its suite passes against the installed 2.0.0 with no change to Burnish's source code. The pin then moved from `v2.0.0` to `v2.1.0` in Burnish 0.3.15, together with the Warden pin, again with no change to Burnish's source code, and from `v2.1.0` to `v2.2.0` in Burnish 0.3.16 (a lightweight tag, so the tag is the commit named in the comment; the `cns` package at v2.2.0 equals v2.1.0 except its version string), together with the Warden pin once more and again with no change to Burnish's source code.

### Bumping the Warden pin

This package depends on one exact Warden commit (see `dependencies` in `pyproject.toml`), so a change on
Warden's `main` cannot break it without anyone noticing. To move to a newer Warden:

1. Pick the Warden commit you want, and note the release it belongs to.
2. Put the full 40-character commit after the `@` in the `warden @ git+...` line of `pyproject.toml`, and the release it
   corresponds to in the comment on that line. The CNS line is different: it is pinned by its release tag
   (`@v2.3.0`), the spelling every repository in the circuit uses, with the commit the tag is in the comment.
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
- **Optional dependencies.** Pins and dependencies in `[project.optional-dependencies]` and `[dependency-groups]` are read
  too. A claim that only an extra backs is not called false: the critic lists it as supported and says it holds for the
  optional dependency only. A module imported only inside a function, behind a `try` that expects the import to fail, or under
  `TYPE_CHECKING` counts as optional. A claim said twice in two phrasings is reported once.
- **A test count.** Burnish counts no tests, so a number the README gives for its suite is reported as unverifiable
  unless a count is supplied: `--collected N` takes the total from `pytest --collect-only -q`, and when the
  finisher runs under Warden the measured suite is used instead. A count that cannot be true is reported either way.
  The simplest honest README states no such number.

### Exit codes and logging

Every command that takes a path reads a folder, and a folder it cannot read has no verdict: a missing path, a path
that is not a folder, a folder with nothing to read (no Python files, or for `readme-critic` no README) and an
unreadable file all exit 2 with the reason on stderr, never "0 findings". `critic` compares the README with the code, so a
folder that holds a README and no Python files also exits 2 ("nothing to check"): a verdict that the story is consistent
with nothing would be empty. `readme-critic` reads a README on its own, and `inspect`, `readme`, `cns` and `finish` still
accept one. A broken symbolic link with a Python name (`.py`) is an unreadable file, and every command that reads Python
says "broken symbolic link" for it. So is a broken link with a README name, for every command that reads or may write the
README (all but `check`), instead of "found no README": a write through it would create its target, wherever that is. `finish` also never proposes an edit to a file that is a symbolic link or lies under one, whether the
link is broken or not; it says so in its notes.
`check` does not follow a symbolic link to a directory (nor does any other command): Python files that can only be reached through
one are not read, and nothing is printed about them. A tree whose only Python is behind such a link has nothing to check and exits 2.

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

This is the standalone, explicit flow, not part of the circuit: to finish a repository, hand Burnish to Warden as the finisher. Nothing
is written without `--authorize`:

```bash
warden tagteam path/to/repo --drafter drafter.seat:Drafter --finisher burnish.finisher:Burnish --ghost-root ../ghost_tools --swizzle-root ../SWIZZLE
```

That command needs a change to govern (a Drafter installed, or the claim seat with `--claim-commit` or `--claim-diff`, which made the Drafter optional) and checkouts of Ghost Tools and SWIZZLE beside the target, and it is a sketch of the shape: the flags exist in the pinned Warden's `warden tagteam --help`, but no test in this repository runs this exact command. Run with `--finisher burnish.finisher:Burnish` and no Drafter, Warden only observes and ends `INCONCLUSIVE` (exit 6) with nothing proposed; that was seen once by hand on 2026-10-22 and no test holds it.

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
999; the measured suite does not match it. These disagree."). It writes no number of
its own that goes stale: no count of passed tests, no count of Ghost findings or change cycles, no pin and no
version. It says whether the suite was green, which kinds of finding Ghost still reports and which checks never ran, so a
repository whose own tests forbid a hard-coded count in its README can keep the section. It judges only claims
about this project's own suite ("all tests pass", "30/30 passing", a bare
full-coverage figure). It does not judge a change ("added 5 tests"), a history ("before the
fix, 10 tests failed"), another thing's count (a version, a file, a table row, a
named subject) or a denial ("we make no claim of full coverage"). Counts it skips
because they belong to something else are only counted, never quoted, so Ghost
Tools does not read the report as a new claim. Skipped tests are not failures: a
claim of 30 passing over 28 passed and 2 skipped agrees, with the skips noted,
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

## What works, and what shows it

Each line names the test, the CI job (`.github/workflows/ci.yml`: `python` on 3.11, 3.12 and 3.13, `rust`, `cpp23`) or the command that shows it. A line with no such pointer would be cut. The tests run against the Warden commit and the CNS tag that `pyproject.toml` names; for this release the suite ran on 3.11, 3.12 and 3.13 with nothing skipped.

- **The Python checker finds eight things.** The checks are `PY-EXC`, `PY-SWALLOW`, `PY-STAR`, `PY-DOC`, `PY-NAME`, `PY-CMP`, `PY-RET` and `PY-TYPE`. `tests/test_checks.py` has a test for each, for example `tests/test_checks.py::test_bare_except_is_found`. A file it cannot parse is a finding, not silence (`tests/test_checks.py::test_unparseable_file_is_reported_not_skipped`).
- **Burnish passes its own checks.** `tests/test_self.py::test_burnish_passes_its_own_python_checks` and `tests/test_self.py::test_burnishes_readme_is_over_the_top_by_its_own_critic`. CI runs `burnish check .`, `burnish critic .` and `burnish readme-critic . --tier over-the-top` in the `python` job.
- **The README critic judges a README against its rules and gives no score.** `tests/test_readme_critic.py`. The sample under Usage is held to the real output by `tests/test_docs_in_sync.py::test_the_readme_sample_is_what_the_readme_critic_says_about_this_repository`.
- **The claims critic compares a README's pin, dependency list and test count with the tree.** `tests/test_drift.py`. Burnish's own README is held to it by `tests/test_self.py::test_burnishes_readme_makes_no_claim_its_tree_contradicts`.
- **Commands fail closed.** A missing path, a path that is not a folder, a folder with nothing to read and an unreadable file exit 2 and say why (`tests/test_cli_fail_closed.py::test_a_path_that_does_not_exist_exits_2_and_says_so`). A broken symbolic link is named as one (`tests/test_cli_fail_closed.py::test_a_broken_py_symlink_among_real_files_makes_every_command_exit_2`).
- **A report nobody received is not a success.** `tests/test_cli_delivery.py` runs each printing command in a real process against a closed pipe, a closed descriptor and a full device, with Python's output buffered and unbuffered (`tests/test_cli_delivery.py::test_a_closed_pipe_is_not_a_traceback_and_keeps_the_earned_code`). The exit-code table above equals the code: `tests/test_cli_ops.py::test_the_readme_exit_code_table_matches_the_code`.
- **The finisher proposes and never writes.** `tests/test_finisher.py::test_the_finisher_proposes_and_never_writes`. `tests/test_independence.py::test_no_burnish_module_opens_a_file_for_writing` looks for the calls `write_text`, `write_bytes`, `unlink` and `rmtree` in the package and finds none; it does not look for other ways to write, and a search for `open(` and `os.replace` on 2026-10-22 also found none, which no test holds.
- **The finisher is a fixed point and edits only between its own markers.** `tests/test_stable_and_careful.py::test_finishing_its_own_output_five_times_changes_nothing`, `tests/test_stable_and_careful.py::test_the_generated_section_is_replaced_only_between_its_markers` and `tests/test_second_red_team.py::test_the_authors_text_is_kept_byte_for_byte_when_the_block_is_added`.
- **The finisher leaves alone what Warden and the Judge would reject.** Test files, CI files, vendored and generated code, fixture and specimen folders, and anything that is or lies under a symbolic link get no edit: `tests/test_second_red_team.py::test_a_protected_file_is_never_proposed_even_for_whitespace`, `tests/test_second_red_team.py::test_a_vendored_or_generated_directory_is_never_proposed` and `tests/test_no_edit_through_a_link.py::test_the_guard_drops_any_edit_whose_path_is_or_lies_under_a_link`. `tests/test_second_red_team.py::test_burnish_agrees_with_warden_about_what_is_protected` compares the list with the installed Warden's.
- **It runs inside the real Warden.** Three tests drive the finisher through the pinned Warden's tag team: `tests/test_finisher.py::test_through_warden_the_code_is_tidied_and_the_readme_keeps_the_authors_words`, `tests/test_finisher.py::test_nothing_to_finish_means_no_proposal` and `tests/test_stable_and_careful.py::test_through_warden_a_second_finish_proposes_nothing`. They follow Warden's held-result rule: a finish that is not a full `ACCEPT` is put back and held, and the test keeps it with a grant before checking the result. `tests/test_warden_pin.py::test_burnish_declares_the_contract_of_the_warden_it_is_pinned_to` checks the contract number.
- **Burnish imports Warden's shapes and no other role.** `tests/test_independence.py::test_no_module_imports_another_role` and `tests/test_independence.py::test_no_burnish_module_counts_tests`.
- **The pins and the CI toolchains are checked.** Warden is a full commit, CNS is a release tag, each pin comment names the release installed (`tests/test_release_hygiene.py::test_every_git_dependency_is_a_full_commit`, `tests/test_release_hygiene.py::test_the_release_in_each_pin_comment_is_the_release_installed`). The Rust release and the g++ and cmake majors are asserted before the build (`tests/test_release_hygiene.py::test_the_rust_job_installs_the_pinned_toolchain_and_asserts_it_before_linting`, `tests/test_release_hygiene.py::test_the_cpp_job_prints_and_asserts_the_compiler_and_cmake_versions_before_building`).
- **The two other language exemplars build.** The `rust` job runs `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings` and `cargo test --locked`. The `cpp23` job builds with GCC 13 and `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror`, then runs `ctest`. All three exemplars read the same `exemplars/vectors.txt`.
- **A pin or a dependency in an extra is read, not ignored.** `tests/test_drift_extras.py::test_a_pin_that_pyproject_declares_in_an_extra_is_not_a_contradiction`, `tests/test_drift_extras.py::test_a_module_declared_in_an_extra_is_not_called_undeclared` and `tests/test_drift_extras.py::test_the_same_dependency_claim_said_twice_is_reported_once`. On 2026-10-24, with this release, `burnish critic` ended 0 on SWIZZLE 3f35dad and ghost_tools 5a9154d, where it had ended 1 on both.
- **A test count written with a separator, a k or a number word is read.** `tests/test_count_forms.py::test_a_thousands_separator_of_any_common_kind_gives_the_whole_number`, `tests/test_count_forms.py::test_a_k_means_a_thousand` and `tests/test_count_forms.py::test_a_number_word_is_a_count`.
- **The generated section states no number that goes stale.** `tests/test_block_has_no_snapshots.py::test_the_section_carries_no_number_that_drifts_with_the_target` renders it for a green and a red suite and finds no count, pin or version in it. `tests/test_block_has_no_snapshots.py::test_the_section_matches_nothing_a_sibling_repository_forbids_in_a_readme` checks four representative cases against the patterns that the README tests of ghost_tools, SWIZZLE, ASSAY, DRAFTER, JUDGE, WARDEN and WATCHER_MCU fail on. The patterns are copies, with the source test named beside each.
- **This README is held to its own rules.** `tests/test_readme_ledger.py` fails if a required section is missing, if a marketing word comes back, if a test this README names does not exist, or if a version or date in the ledger below disagrees with `CHANGELOG.md`.

## What does not work, or is not proven

- **Most of the criteria are not built.** Naming, narrative comments, inline architectural comments, guards and function splits are designed (`PA`, `PB`, `PC`, `R1` to `R4`) and have no rewriter. Today the code tidy removes trailing whitespace and adds a missing final newline, and nothing else. `burnish criteria` prints which criteria are implemented and which are only designed.
- **Rust and C++23 code is not checked by Burnish.** Their criteria are written down, and each has one small exemplar built by that language's own tools in CI. That shows two programs build and agree on one vector file. It does not show Burnish can judge anyone else's Rust or C++.
- **The C++ exemplar is proven on one compiler.** CI builds it with GCC 13 only. On 2026-10-22 I built it with Clang 18.1.3 and libstdc++ 13 and it failed (`no member named 'unexpected' in namespace 'std'`), as `docs/languages/cpp23.md` says. Clang with libc++, a newer libstdc++ and MSVC were not tried. No test holds the Clang result.
- **Only Linux has been run.** CI uses `ubuntu-24.04` and `ubuntu-latest`. Nothing here has been run on macOS or Windows. Some tests in `tests/test_cli_delivery.py` carry conditional skip markers (a system without POSIX pipes, a machine without `/dev/full`); on the CI runners and in the runs for this release none was skipped. No test uses `xfail`.
- **Ghost Tools still reports findings on this repository.** The circuit run recorded 38 at the start and 38 at the end, none new, at 0.3.11 and again at 0.3.12 (see Self-hosting). They have not been worked off, and the Judge accepts because none is new. Their kinds are not listed here; run Ghost Tools to see them.
- **"Optional" is decided by where an import sits, not by how it is used.** A module imported inside a function counts as optional even if that function always runs, so a README that says "no runtime dependencies" can be backed by a hard dependency hidden in a function. Only an import at the top of a module counts as needed to load it.
- **Burnish alone does not govern a change.** It needs Warden, a human grant, something that proposes the change (the claim seat or a Drafter) and the other instruments. Through the real Warden, only the three tests named above exercise the finisher. The recorded runs of the whole loop with Burnish in its seat (Warden's `docs/REGISTRY.json`, rows 3 to 5, dated 2026-10-14, Warden 0.11.0 and 0.11.1) used scratch repositories and fresh clones of the circuit's own repositories, and nothing from them was committed. No real outside repository has been transformed by the loop with Burnish in its seat.
- **The top README tier is Burnish's own standard.** The minimum and strong tiers come from the sources listed in `docs/README_STANDARD.md`. The over-the-top tier is a synthesis the standard says it sets for itself, not a rule any source states. The critic reads one README and the files it links to; it does not fetch URLs and cannot tell whether prose is clear.
- **The critics find claims by phrasing.** Details are under Known defects.
- **Burnish's section still quotes unbacked status phrases.** When a README makes an unbacked status claim, the generated section repeats the words with a note that no measurement backs them (`tests/test_stable_and_careful.py::test_a_readme_that_claims_more_tests_than_were_measured_is_told_so_and_left_as_written`). On 2026-10-14 a Ghost detector once read that quote as a new claim and the run was rejected (see the ledger, 0.2.0). That was fixed on Ghost's side. Whether the current Ghost reads the quote again is not tested here.
- **A mention of a version or a count that the critics skip is not checked.** Counts about a file, a table row, a version or a named subject are only counted, never judged.

## Known defects (open)

- **The test-count check misses wordy counts.** It reads digits (with a comma, dot, space, apostrophe or underscore between thousands), a number of thousands such as "1k", and number words from two to 999 ("twelve", "twenty-one", "two hundred"). It does not read "about a thousand tests pass", "a couple of hundred tests pass", "1.5 million tests pass" or a number worded above 999, and none of those is misread as a smaller count (`tests/test_count_forms.py::test_wordier_counts_are_still_missed_and_never_misread_as_a_smaller_number`). `tests/test_readme_ledger.py::test_the_worded_test_count_gap_is_still_open` holds this sentence to the code: it fails the day the gap closes, so this line must then be removed.
- **Python files that start with a byte order mark are skipped, not tidied.** Warden's own syntax check cannot read them, so the file is left alone and a note says so (`tests/test_stable_and_careful.py::test_a_python_file_with_a_bom_is_left_alone`).
- **A README that ends inside an unclosed code block is left alone,** so it gets no generated section (`tests/test_stable_and_careful.py::test_a_readme_that_ends_inside_a_code_fence_is_left_alone`).
- **A `README.rst`, `README.txt` or `README` with no extension is not changed.** Burnish says so in its notes and reports a count mismatch there, but writes no section (`tests/test_stable_and_careful.py::test_an_unsupported_readme_is_not_converted_and_no_markdown_one_appears`).
- **The protected-file list is a copy of Warden's.** A change in Warden's guard needs a change in `burnish/files.py`. The test that compares the two runs against the installed Warden, so it catches drift when the Warden pin moves (`tests/test_second_red_team.py::test_burnish_agrees_with_warden_about_what_is_protected`), not between pin moves.
- **A file nested deeper than Python can compare is read by `check` and left alone by `finish`.** An unbroken run of unary minus signs thousands long parses on some Python versions and not on others. Where it parses, `check` reports it like any file while `finish` leaves it untidied and says it is nested too deeply to tidy safely; where it does not, `check` reports that the file could not be parsed. Neither crashes (`tests/test_small_fixes.py::test_check_and_finish_both_name_a_file_that_is_too_deep`). They do not give the same answer for the middle depths.
- **The patterns that guard the generated section are copies.** They were read from the other repositories' README tests on 2026-10-23. If one of those tests changes, `tests/test_block_has_no_snapshots.py` does not notice; a person has to copy the new pattern.
- **A README that Burnish compiles from nothing still states a module count and the package version.** A repository with no README gets one built from its tree once ("Python modules in this tree" and the version), and then it belongs to the author. Those two figures go stale, and no test holds the compiled README to the sibling patterns. The generated section at the end of any README is held; the compiled body is not.
- **The README critic's size details are not in the section.** A gap whose reason holds a number (for example how many lines a README has) is written with its rule and plain reason and without the number, so a reader of the section does not see how long the README was. The command line still prints the number.
- **The exact cmake release is not pinned.** The `cpp23` job asserts the cmake major version only, because the runner's cmake changed between runs. Pinning the release would need a pip-installed cmake.
- **A broken stderr is out of scope.** If the one-line message about an undelivered report cannot be written either, the exit code is all there is. No test holds this.

## What broke and how it was fixed

Newest first. Each entry says what was wrong, how it was found when that is known, the version that fixed it, and what now stops it coming back: a named test, or "no test yet". The sources are `CHANGELOG.md`, `git log` and the tests. Where a fix was incomplete or wrong, the entry says so. Open problems are under "Known defects (open)". Before 0.3.0 the version string stayed 0.2.0 while the work went on, so the entries under 0.2.0 carry the dates and commits of the fixes.

**0.3.19** (2026-10-30)
- *`burnish check` called a file Python cannot compile clean.* `checks.py` read files with `errors="replace"`, so a `.py` file with a literal 0xff byte was repaired in memory and `burnish check` reported "0 finding(s)" with exit 0, while `burnish finish` on the same file said "not valid UTF-8". Found by the round-8 audit. The file is read strictly now: it is a finding that says so, and `check` exits as it does for any finding; `finish` is unchanged. Guard: `tests/test_undecodable_file.py::test_an_undecodable_python_file_is_a_finding_that_says_why`.
- *Text that described the old loop.* The README and `STACK.md` still said the Drafter is needed and that the finisher runs in the loop; they now say the Drafter is optional, Burnish is released from the circuit and Warden seats it only with `--finisher`. No test.

**0.3.18** (2026-10-30)
- The Warden pin moved from `df212db` to `cb45681`. No Burnish code changed.

**0.3.17** (2026-10-30)
- The Warden pin moved from `fade3ca` to `df212db`. No Burnish code changed.

**0.3.16** (2026-10-30)
- The CNS pin moved from `v2.1.0` to `v2.2.0` and the Warden pin from `fe9c8b3` to `fade3ca`. No Burnish code changed.
- 2026-10-31: the CNS pin moved from `v2.2.0` to `v2.3.0` and the Warden pin to the commit named in `pyproject.toml`, so the circuit installs one CNS release. No Burnish code changed.

**0.3.15** (2026-10-29)
- The CNS pin moved from `v2.0.0` to `v2.1.0` and the Warden pin from `68f2a95` to `fe9c8b3`. No Burnish code changed.

**0.3.14** (2026-10-29)
- The README says the owner released Burnish from the circuit on 2026-10-29. No code, test, history or CI changed.

**0.3.13** (2026-10-24)
Found by the round-6 independent audit of the final release set on 2026-10-23 and 2026-10-24; each item was reproduced before it was changed, on throwaway clones of SWIZZLE 3f35dad and ghost_tools 5a9154d (and also checked on the newer SWIZZLE 6853c92 and ghost_tools 3df51b3).
- *The claims critic ignored optional dependencies.* It read only the runtime dependencies, so `burnish critic` ended 1 on SWIZZLE with "pyproject.toml pins no git dependency" although SWIZZLE pins CNS in its `cns` extra, and on ghost_tools with an `anthropic` that is declared in its `semantic` extra "imported but not declared". Modules SWIZZLE imports lazily (`warden`, `ghost_buster`, `pydantic`) were reported as undeclared dependencies too. The finisher wrote those false disagreements into a README section. Fixed in 0.3.13: extras and dependency groups are read, a claim only an extra backs is listed as supported and said to hold for the optional dependency only, and a module imported only inside a function, behind a `try` that expects the import to fail, or under `TYPE_CHECKING` is optional. Guard: `tests/test_drift_extras.py::test_a_pin_that_pyproject_declares_in_an_extra_is_not_a_contradiction`, `tests/test_drift_extras.py::test_a_module_declared_in_an_extra_is_not_called_undeclared` and `tests/test_drift_extras.py::test_modules_imported_only_inside_a_function_or_a_guarded_try_are_optional`. The lazy-import rule is a heuristic; the limit is under Known defects.
- *The same dependency claim was printed twice.* A README that says "no runtime dependencies" in one place and "no runtime dependency" in another got two identical lines. Fixed in 0.3.13. Guard: `tests/test_drift_extras.py::test_the_same_dependency_claim_said_twice_is_reported_once`.
- *A test count written with a separator, a k or a number word was misread or missed.* "1 374 tests pass" was read as a count of 374 (the first group dropped), and "1.374", "1k" and "twelve" were not read. Fixed in 0.3.13 for separators, a k and number words up to 999; wordier counts are still missed and never misread as a smaller one (Known defects). Guard: `tests/test_count_forms.py::test_a_thousands_separator_of_any_common_kind_gives_the_whole_number` and `tests/test_count_forms.py::test_wordier_counts_are_still_missed_and_never_misread_as_a_smaller_number`.
- *`main()` replaced standard output with None for the caller after a failed delivery.* A test or a library calling it in-process found its stream gone. Fixed in 0.3.13: `main()` leaves the stream as it found it, and the new process entry point `run()` (the console script, `python -m burnish.cli`) still neutralises a dead stream for the flush at exit. Guard: `tests/test_small_fixes.py::test_main_puts_standard_output_back_after_a_reader_left` and `tests/test_small_fixes.py::test_the_process_entry_point_still_neutralises_a_dead_stream_for_the_flush_at_exit`.
- *`burnish check` crashed on a file nested deeper than the parser.* An unbroken run of unary minus signs ended in a RecursionError or MemoryError traceback while `finish` left the file alone. `check` now reports that the file could not be parsed and `finish` gives the true reason. They still differ at middle depths (Known defects). Guard: `tests/test_small_fixes.py::test_check_reports_a_file_the_parser_cannot_take_instead_of_crashing` and `tests/test_small_fixes.py::test_check_and_finish_both_name_a_file_that_is_too_deep`.
- *The claims critic's heading said "Poetry critic"* and a link to a directory was skipped by `check` without a word. The heading now says "Claims critic" and the README says links to directories are not followed. Guard: `tests/test_small_fixes.py::test_the_critic_heading_names_the_claims_critic_not_poetry` and `tests/test_small_fixes.py::test_a_link_to_a_directory_is_not_followed_by_check_and_the_readme_says_so`.
- *The self-hosting paragraph said no fresh run was recorded,* and the README did not say Ghost still reports findings on Burnish itself. Both were stale once the circuit's run was recorded; the paragraph and the Known defects now say what the record holds. Guard: `tests/test_readme_ledger.py::test_the_self_hosting_paragraph_cites_the_record_and_holds_its_numbers`.

**0.3.12** (2026-10-23)
- *The generated section wrote numbers that go stale, and two sibling repositories fail on exactly that.* The section carried the suite's counts (passed, failed, skipped and the rest), how many findings Ghost still reported, how many change cycles ran, the measured counts inside the disagreement sentence, a pin commit inside a drift note and the size of the README going into the finish. SWIZZLE and JUDGE each have a test that fails on a pass count in their README, so the finishing change broke their suites, Warden put it back, and the finisher could never finish either repository (`FINISH_REJECTED`). The four repositories that were accepted kept a number that is wrong at the next new test. Found by running the whole circuit over the circuit's own repositories on 2026-10-22 and 2026-10-23, not by any test here. Fixed in 0.3.12: the section says green or not green, which kinds of finding remain and which checks never ran, and states no count, pin or version. Guard: `tests/test_block_has_no_snapshots.py::test_the_section_carries_no_number_that_drifts_with_the_target` and `tests/test_block_has_no_snapshots.py::test_the_section_matches_nothing_a_sibling_repository_forbids_in_a_readme`. The guard was first written as a failing test, before the fix.

**0.3.11** (2026-10-22)
- *The README stated things that were not true.* It listed "the tidy still reaches test files" as a known defect when the finisher never proposes a test file; it said nothing is `IMPLEMENTED` unless Burnish enforces it when three criteria are `IMPLEMENTED` with Warden as owner; it said no tests are skipped when some carry conditional skip markers; and it said the rules were cut to headings in one edit in Warden, which could not be verified. Found while checking every line of the old README against the tests and the code for this rewrite. Guard: `tests/test_readme_ledger.py`, which holds the sections, the named tests, the ledger dates, the check and tier counts and the skip markers to the tree. A sentence it does not name is still only as good as the author's check.

**0.3.10** (2026-10-22)
- *A closed pipe ended in a traceback.* `burnish readme-critic . --tier over-the-top | head -3` ended in a `BrokenPipeError` traceback (exit 1, or exit status 120 when Python's output is buffered), and so did every command that prints. A closed standard output was a silent exit 0 and a full device was a traceback. The CHANGELOG does not say how it was found. Now one line on stderr says why, an earned 1 or 2 is kept, and an earned 0 becomes the new exit code 3. Guard: `tests/test_cli_delivery.py::test_a_closed_pipe_is_not_a_traceback_and_keeps_the_earned_code`, `tests/test_cli_delivery.py::test_a_closed_standard_output_is_reported_and_never_exits_0` and `tests/test_cli_delivery.py::test_a_full_device_is_reported_and_never_exits_0`.
- *`critic` on a README with no code said the story was consistent.* A folder holding only a trivial README got exit 0 for a verdict that compared the README with nothing, while an empty folder already exited 2. Now exit 2. Guard: `tests/test_cli_fail_closed.py::test_critic_on_a_readme_with_no_code_says_there_is_nothing_to_check`.
- *The CI workflow had no `permissions:` block,* so its jobs ran with the repository's default token. Guard: `tests/test_release_hygiene.py::test_the_workflow_token_is_read_only_for_every_job`.

**0.3.9** (2026-10-21)
- *`STACK.md` called CNS private.* CNS is public: an unauthenticated request returns 200 and CI installs it without a token. This README never said so. No test held it until this README's test file was added. Guard: `tests/test_readme_ledger.py::test_the_stack_doc_does_not_call_the_public_cns_repository_private`.
- *The C++ gate was described wrongly.* `burnish languages` and the README table said `g++ -std=c++23 -Wall -Wextra -Wpedantic -Werror` or `-Werror` alone; CI runs cmake, and `CMakeLists.txt` sets the flags listed under What works. Guard: `tests/test_docs_in_sync.py::test_the_cpp_warning_flags_the_docs_name_are_the_flags_cmake_sets`.
- *The Rust and C++ toolchains floated.* A new stable Rust or a new `ubuntu-latest` could turn CI red by itself. Rust is now pinned by `exemplars/rust/rust-toolchain.toml` and the C++ job asserts the g++ major version. The first fix was wrong: it asserted cmake 3.28, the real CI run failed because the runner had 3.31.6, and it now asserts the major version only (commit `fab7a97`). Guard: `tests/test_release_hygiene.py::test_the_rust_toolchain_is_one_exact_release_with_the_tools_ci_runs` and `tests/test_release_hygiene.py::test_the_cpp_job_prints_and_asserts_the_compiler_and_cmake_versions_before_building`.

**0.3.6** (2026-10-21)
- *Two pins that could not be installed together.* Warden's pin asked for one CNS commit, while the CNS tag that `main` had just moved to conflicted with it in a single environment. This branch kept the older CNS commit that Warden's pin itself needed, so the install resolved. Later releases moved both pins forward together. No test holds the resolution; the `python` CI job's `pip install -e ".[dev]"` step is what fails if it breaks.

**0.3.5** (2026-10-21)
- *A broken README link was read as "no README".* `critic`, `inspect`, `readme`, `cns` and `finish` treated it that way, so `finish` proposed creating `README.md` over it, and a write through a dangling link creates its target wherever that is. They now exit 2 with "broken symbolic link", and the finisher drops any edit whose path is a link or lies under one. Guard: `tests/test_cli_fail_closed.py::test_a_broken_readme_symlink_makes_every_command_that_reads_or_writes_the_readme_exit_2` and the tests in `tests/test_no_edit_through_a_link.py`.

**0.3.4** (2026-10-21)
- *A dangling `.py` link was skipped in a tree with real files,* and the command exited 0 while `check` exited 2. `readme-critic` on a dangling README link said it found no README. All now exit 2 with the reason. Guard: `tests/test_cli_fail_closed.py::test_a_broken_py_symlink_among_real_files_makes_every_command_exit_2` and `tests/test_cli_fail_closed.py::test_a_broken_readme_symlink_is_named_as_one_by_readme_critic`.

**0.3.2** (2026-10-17)
- *The README's critic sample was output about another repository,* and listed four failures under a headline that said five. It is now regenerated from the real command and a test compares them. Guard: `tests/test_docs_in_sync.py::test_the_readme_sample_is_what_the_readme_critic_says_about_this_repository`.
- *The Rust job was not reproducible.* `Cargo.lock` was in `.gitignore`, and the two GitHub Actions were not pinned to commits. The lock file is committed, CI builds with `--locked`, and the actions are pinned. Guard: `tests/test_release_hygiene.py::test_the_rust_exemplar_lockfile_is_committed_and_ci_builds_with_it_locked` and `tests/test_release_hygiene.py::test_every_action_is_pinned_to_a_full_commit_with_its_tag_in_a_comment`.
- *A broken `.py` link in `check` gave whatever error the read happened to raise.* It now says "broken symbolic link". Guard: `tests/test_cli_fail_closed.py::test_a_broken_symlink_makes_check_exit_2_and_names_the_true_reason`.

**0.3.0** (2026-10-17)
- *Commands said "0 finding(s)" for a path they could not read.* A missing path, a non-folder, a folder with nothing to read or an unreadable file exited 0. They now exit 2. Guard: `tests/test_cli_fail_closed.py`.
- *A README could state a pin, a dependency list or a test count the tree contradicted, and nothing checked it.* The claims critic (`burnish/drift.py`) was added. Guard: `tests/test_drift.py`.
- *`mypy` and `ruff` found errors* (typing gaps in the package and tests, one unused import) and neither was a gate. Both are fixed and both run in CI. Two narrow, commented `# type: ignore[arg-type]` remain, in `tests/test_stable_and_careful.py` (a test that passes a bare string on purpose) and `tests/test_cli_fail_closed.py` (a wrapper that forwards its arguments unchanged). Guard: the `ruff check .` and `mypy` steps in the `python` job; no other test.
- *A closed output pipe was reported as "cannot read a file".* Fixed in 0.3.0 for that message; the wider pipe problem was still open and was fixed in 0.3.10. No separate test.

**0.2.0** (2026-10-08 in the CHANGELOG; the fixes below landed up to 2026-10-14)
- *The finisher appended template filler to a README that was already well structured* (found by running the loop on CNS, 2026-10-08, commit `0bdfc01`). It now adds only its one marked section and never writes em or en dashes in generated text. Guard: `tests/test_finisher.py::test_no_template_filler_is_written_into_an_existing_readme` and `tests/test_finisher.py::test_generated_text_has_no_em_or_en_dash_and_the_authors_text_is_left_alone`.
- *An empty findings list read as clean* (2026-10-08, commit `c19510d`). The commentary now says which checks never ran. Guard: `tests/test_finisher.py::test_the_commentary_says_when_a_check_never_ran`.
- *The finisher was not a fixed point and wrote outside its own text* (2026-10-09, commit `7fcb4f0`, from a red-team review). A second run proposed more, the critic read its own output, and encodings, byte order marks and line endings were mishandled. It now edits only between its markers and proposes nothing on its own output. Guard: `tests/test_stable_and_careful.py::test_finishing_its_own_output_five_times_changes_nothing`, `tests/test_stable_and_careful.py::test_a_crlf_readme_stays_crlf_and_its_own_lines_are_not_rewritten` and `tests/test_stable_and_careful.py::test_ghost_text_with_a_forged_section_cannot_make_a_line_of_its_own`.
- *The finish could be rejected whole* (2026-10-10, commit `b0963ac`, a second red-team review). It proposed whitespace edits to test files and CI files, which the Judge rejects, and its README section carried phrases Ghost read as new test-count claims. It now never proposes those files, and by default proposes only the README. Guard: `tests/test_second_red_team.py::test_a_protected_file_is_never_proposed_even_for_whitespace`, `tests/test_second_red_team.py::test_warden_would_accept_every_edit_burnish_proposes` and `tests/test_second_red_team.py::test_the_block_does_not_contain_a_phrase_ghost_reads_as_a_test_count_claim`.
- *The README gave a test count that did not match the suite, and stale install text* (2026-10-12, commit `d0432cc`). Corrected then; the count was later removed altogether, because it went stale at the first new test. Guard: `tests/test_self.py::test_burnishes_readme_makes_no_claim_its_tree_contradicts`.
- *Three tests expected a finish to stand after `ACCEPT_UNVERIFIED`* (2026-10-12, commit `c61f8f6`), which Warden v0.10.0 no longer allows: it holds such a run and puts the tree back. The three tests were changed, not the finisher: each now keeps the held result with a grant before checking it, and the assertions on the kept result were left as they were. They are the three tests named under What works.
- *The tidy reformatted answer-key files* (2026-10-14, commit `1ec3ec8`). When the circuit governed a clone of ASSAY, the code tidy reformatted its specimen files, which are deliberately degraded, and only the ASSAY suite's recorded hashes caught it. Burnish now skips fixture, specimen, test-data, golden, snapshot and corpus folders. Guard: `tests/test_second_red_team.py::test_a_vendored_or_generated_directory_is_never_proposed`, which lists those folders.
- *A critic note fed Ghost a new finding.* In Warden's registry (row 4, 2026-10-14), the first run on a scratch repository ended `FINISH_REJECTED` because Ghost's new status-claim detector read Burnish's note about a status claim in the scratch README as a fresh claim, and its ids moved with line numbers. Both were fixed in Ghost, not in Burnish, and the run was repeated. Burnish still quotes such phrases (see "What does not work"). The guard on Burnish's side covers counts only: `tests/test_second_red_team.py::test_the_block_does_not_contain_a_phrase_ghost_reads_as_a_test_count_claim`. No test here covers the status-word case.

## Self-hosting

The whole circuit, as it stood before the owner released Burnish from it (2026-10-29), was run over this repository on 2026-10-22 and 2026-10-23. The counts below are dated records of that run. The record is the CNS repository's `docs/evidence/SELFHOSTING_2026-10-23.md` (on the CNS branch `claude/horsemen-production-status-5wsndb` until that branch is merged), with the run records beside it, in https://github.com/wking53214/CNS. For Burnish it records two runs, each ending `ACCEPT`: one on commit `cd17eec` (0.3.11) and one on commit `c23ed87` (0.3.12), both with 7 declined-check gaps and 38 Ghost findings standing, none new. The README section the circuit kept was Burnish's own generated section, and nobody reviewed it. The same record shows the first run over SWIZZLE and JUDGE ending `FINISH_REJECTED` because this repository's finisher wrote the suite's pass count into their READMEs, which their own tests forbid; that was fixed in Burnish 0.3.12, and both ended `ACCEPT` on the re-run.

What the record does not mean: an `ACCEPT` here carries 7 gaps, the Ghost checks that are declined by design (`mutate`, `kernel`, `structure`, `tests`, `project`, `secrets` and `correlate`). It does not mean there are no secrets, no weak tests, no mutation survivors and no structural problems, and the Judge accepted with Ghost findings still standing because it measures only that none are new. The record also does not cover this commit or Warden 0.13.10 (a dated statement: Warden has moved on since).

## Ceilings code cannot fix

- The repository is young. Its history starts on 2026-10-08.
- It has one human maintainer, and most commits were written with an AI assistant (the commit trailers say so).
- It has no known outside users.
- The owner released it from the Horsemen circuit on 2026-10-29 (see the status note under What this is). Nothing in it was removed, and it keeps working on its own.
- Releases are tagged by the owner, not by the code. Check the repository's tags and releases on GitHub for what exists.

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

- No Burnish module writes or deletes a file (`tests/test_independence.py::test_no_burnish_module_opens_a_file_for_writing`, with the limit described under What works).
- No Burnish module counts tests or imports another role (Drafter, Ghost Tools, SWIZZLE, ASSAY). What it says about the suite or about defects, it quotes from the facts Warden hands it.
- No Python or README criterion is marked `IMPLEMENTED` unless it names a check that exists, and nothing is marked `IMPLEMENTED` for Rust or C++23 (`tests/test_docs_in_sync.py::test_a_python_criterion_marked_implemented_has_a_check`, `tests/test_docs_in_sync.py::test_nothing_is_marked_implemented_for_a_language_burnish_does_not_check`). A few criteria (`R5`, `R7`, `R9`) are marked `IMPLEMENTED` with Warden as their owner.
- Burnish passes its own Python checks and its own README critic at the over-the-top tier.
- The criteria table and the documents cannot disagree (`tests/test_docs_in_sync.py::test_every_criterion_is_written_up_in_the_docs`).

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

**Can it fix my code?** Not by itself. Proposing a fix is a Drafter's job (Warden seats one with `--drafter`; it is optional since the claim seat, and it is released from the circuit like Burnish). Burnish, when Warden seats it with `--finisher`, runs once after the loop and proposes a tidy and the final README. Warden, with a human grant and a green suite, decides. Today the tidy removes trailing whitespace and nothing else.

**Why does it check Python but not Rust or C++?** Because only Python has a
checker. Rust and C++23 have written criteria and a working exemplar, and the
language's own tools enforce the exemplar in CI. `burnish languages` says so.

**Why is the critic so harsh?** Because a critic that praises is a brochure. The
README critic is allowed, and required, to say a README is not good.

**What does it not own?** Writing to a repository, the test gate, the SWIZZLE proof gate and the audit file are Warden's, behind a human grant. Forensic detection of long functions, dead code and duplicates, and counting tests, are ghost_tools'. Proposing fixes is a Drafter's, which is optional (any actor's change can enter through Warden's claim seat). Burnish also does not judge whether prose is clear or an image is good, fetch URLs, tell a dead external link, or score anything.

## Alternatives

Formatters and linters such as ruff, black, clippy and clang-tidy enforce
style on one language and should be used alongside this. READMEs have templates
and spec checkers such as Standard Readme. Burnish differs in two ways: it
keeps the criteria, the languages and the README standard in one place that
checks itself, and it separates the opinion about better code from the
authority to change it.

## Roadmap

Outstanding, in the order a person would likely want them:

1. A first rewrite for names or comments in the finisher, behind Warden's gate.
2. Read the parts of the C++ Core Guidelines the first pass missed, and add their criteria.
3. A Rust checker, if Clippy's lints are not enough.
4. (Superseded by the release of Burnish and Drafter from the circuit on 2026-10-29; kept as history.) Run Warden's loop with Drafter and Burnish in their seats on a real repository and record it in Warden's registry. The loop has run with every seat live on a scratch repository (2026-10-14, `warden tagteam --stack`; under a `code` grant Burnish's tidy and README section were both applied and the run ended `ACCEPT`), and that run is in Warden's `docs/REGISTRY.json`; a real repository is still to do.

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
