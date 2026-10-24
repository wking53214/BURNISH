# Changelog

All notable changes to Burnish are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Releases of this version are not tagged yet: tagging is the
owner's decision and has not been made. A tag named `v0.10.0` does exist, left over from the earlier Streamline numbering
before the rename; it is higher than 0.3.x and does not correspond to any version recorded here. The links at the foot of
this file therefore point at commits (compare views between them), not at tags. Each version's link ends at the last commit
before the commit that sets that version, which cannot name itself. The `[Unreleased]` link is a compare view that starts at
the commit that set the latest version and ends at the head commit the link names; a commit cannot name itself, so it lags
the true head by the commit that last wrote it.

## [Unreleased]

## [0.3.13] - 2026-10-24

Found by the round-6 independent audit of the final release set (2026-10-23 and 2026-10-24). Each item was reproduced first.

### Changed
- Step 1: Warden is re-pinned from `b57b81e1c98333c43d422666c89a8fcf3ae6eaca` (0.13.9) to the full commit
  `9ecd1124e6c1b1c4ad7daed37b17f9009662dd9d` (Warden 0.13.10, not tagged). The `Warden.git` spelling and the CNS tag `@v2.0.0`
  are unchanged. The drift-test fixtures use the new commit and version.
- Step 2: `burnish/drift.py` reads `[project.optional-dependencies]`, PEP 735 `[dependency-groups]` and Poetry's groups. A pin or
  dependency that only an extra backs is no longer a contradiction: `claims_held_by_extras` reports it, the critic lists it as
  supported and says it holds for the optional dependency only, and `readme-critic` does not fail on it. A module imported only
  inside a function, behind a `try` that expects the import to fail, or under `TYPE_CHECKING` is optional. `burnish critic` exits 0
  on SWIZZLE 3f35dad and ghost_tools 5a9154d, where it exited 1 on both (the newer SWIZZLE 6853c92 and ghost_tools 3df51b3 were
  checked too). The same note found through two sentences is reported once.
- Step 3: a test count written with a comma, dot, space, apostrophe, underscore or non-breaking space between groups of three
  digits, with a k ("1k", "1.4K"), or as a number word from two to 999 is read. "1 374 tests pass" had been read as 374.
- Step 4: the critic's heading is "Claims critic: <target>"; `main()` leaves `sys.stdout` as it found it and the new `run()` is
  the process entry point (`[project.scripts]` and `python -m burnish.cli`); `check` reports a file nested too deeply to parse
  instead of crashing and `finish` says "is nested too deeply to tidy safely"; the README says links to directories are not followed.
- Step 5: the README's self-hosting paragraph cites the CNS repository's `docs/evidence/SELFHOSTING_2026-10-23.md` and what it
  recorded for Burnish (two runs, each ACCEPT, 7 declined-check gaps, 38 Ghost findings standing, none new), what that does not
  mean, and the SWIZZLE and JUDGE first-run failure that Burnish 0.3.12 fixed. It also says Ghost still reports findings here.
- Step 6: version 0.3.13, this entry and the README ledger.

### Added
- `tests/test_drift_extras.py`, `tests/test_count_forms.py`, `tests/test_small_fixes.py`, and three tests in
  `tests/test_readme_ledger.py` that hold the self-hosting numbers (copied as constants naming the evidence file).

### Existing tests edited
- Step 3: `tests/test_readme_ledger.py::test_the_worded_test_count_gap_is_still_open` held "ninety tests pass" as an open gap;
  it now holds "about a thousand tests pass" and asserts "ninety tests pass" is read.
- Step 4: `tests/test_cli_fail_closed.py::test_critic_still_reads_a_trivial_readme_beside_code` asserted the heading
  "# Poetry critic"; it asserts "# Claims critic".
- Step 1: `tests/test_drift.py` and `tests/test_block_has_no_snapshots.py`, the Warden commit and release strings only.

## [0.3.12] - 2026-10-23

### Changed
- The generated README section states no number that goes stale. It said how many tests passed, failed, errored and were skipped
  ("Warden ran the target's suite at the end of the loop: 1374 passed, ..."), how many findings Ghost still reported and of
  which kinds, how many change cycles ran, the measured counts inside the sentence that says a README's own count disagrees,
  and, inside a drift note, the pin commit, the pin tag and how many files import a module. It now says whether the suite was
  green or not green (and whether something failed, errored, was skipped or was expected to fail), which kinds of finding Ghost
  still reports, which checks never ran, and that a README count does not match the measured suite. A README critic gap whose
  reason holds a number (lines, bytes, code blocks) is written with its rule and plain reason and without the number. The
  command line keeps every detail it had: they are live there.
- Why: running the whole circuit over the circuit's own repositories on 2026-10-22 and 2026-10-23 showed that SWIZZLE and JUDGE
  each have a test that fails on a pass count in their README. The finishing change broke their suites, Warden put it back, and
  the finisher ended `FINISH_REJECTED` for both. The four repositories that were accepted kept a count that goes stale.
- Warden and CNS pins are unchanged.

### Added
- `tests/test_block_has_no_snapshots.py`: renders the section for representative facts and fails on a suite count, a Ghost or
  cycle count, a pin, a version or any other standalone number except the README author's own claimed count; and checks four
  cases against the union of the patterns that the README tests of ghost_tools, SWIZZLE, ASSAY, DRAFTER, JUDGE, WARDEN and
  WATCHER_MCU fail on (copied as constants, each naming its source test), with a control that the patterns fail on the old line.
  It was written first and failed before the fix.

### Existing tests edited
All because they asserted the exact text this release removes (the measured counts, the Ghost count) or relied on the pass count
changing the section. Nothing else about them changed.
- `tests/test_critic.py`: `test_a_green_suite_is_quoted_from_the_facts` (says green, no count),
  `test_the_critic_checks_a_readme_test_count_against_the_measured_suite` (the disagreement sentence).
- `tests/test_finisher.py`: `test_through_warden_the_code_is_tidied_and_the_readme_keeps_the_authors_words`,
  `test_the_review_section_quotes_the_measured_suite` (green, no count), `test_ghost_findings_are_summarised_not_listed` (kinds, no
  count).
- `tests/test_second_red_team.py`: `test_skipped_tests_are_not_a_disagreement_unless_the_readme_says_none_are_skipped` (skips
  noted, not counted); `test_a_mixed_ending_readme_with_a_block_keeps_every_line_ending_when_the_block_changes` and
  `test_a_block_that_ends_the_file_without_a_final_newline_stays_that_way` (they changed the pass count to make the section change;
  they now make the suite fail, which still changes it).
- `tests/test_stable_and_careful.py`: `test_the_generated_section_is_replaced_only_between_its_markers` (same change of input),
  `test_a_readme_that_claims_more_tests_than_were_measured_is_told_so_and_left_as_written`,
  `test_an_unsupported_readme_is_not_converted_and_no_markdown_one_appears`, `test_through_warden_a_second_finish_proposes_nothing`
  (the disagreement sentence).
- `tests/test_readme_ledger.py` (added in 0.3.11): the check that no test is expected to fail matched the text `xfail` inside the
  field name `xfailed`; it now looks for the pytest marker or call, which is what the README sentence it guards is about.

## [0.3.11] - 2026-10-22

### Changed
- CNS is re-pinned from the tag `v1.9.0` to the tag `v2.0.0`, spelled
  `cns @ git+https://github.com/wking53214/CNS.git@v2.0.0` with the comment
  `# v2.0.0 = b13e5d2f9e0e4291725f82794b89117c3d840ac1` (the annotated tag peels to that commit). In a fresh environment on
  3.11, 3.12 and 3.13 the installed `cns` records the requested revision `v2.0.0` and that commit, and the suite passes against
  it with no change to Burnish's source. Burnish imports `cns.seat`, `cns.suite`, `cns.epistemic` and `cns.defect`, and not
  `cns.stack`.
- Warden is re-pinned from `380894f0304ef40587dd29efd41b4ceccf94a5d3` (0.13.8) to the full commit
  `b57b81e1c98333c43d422666c89a8fcf3ae6eaca` (Warden 0.13.9, not tagged). The `Warden.git` spelling is unchanged. Burnish pins
  no other circuit repository, so nothing else moved. `pip install -e ".[dev]"` resolves and `pip check` is clean on all three
  Pythons.
- The README is rewritten around what works (each line names a test, a CI job or a command), what does not work or is not
  proven, the open defects, the ledger of what broke and how it was fixed, self-hosting, and the limits of one young
  repository. The content that was already true was kept.

### Fixed
- The README listed "the tidy still reaches test files" as a known defect. It is false: the finisher never proposes a test file,
  and `tests/test_second_red_team.py::test_a_protected_file_is_never_proposed_even_for_whitespace` holds that. The line is gone.
- The README said nothing is called `IMPLEMENTED` unless Burnish enforces it. The criteria `R5`, `R7` and `R9` are `IMPLEMENTED`
  with Warden as their owner; the sentence now says what the tests check.
- The README said no tests are skipped. Some tests in `tests/test_cli_delivery.py` carry conditional skip markers; none was
  skipped in the CI runs or the release runs. The README now says that.
- The README said the rules were cut to headings in one edit in Warden. That could not be verified and is replaced by Warden's
  commit `81cd431`, whose message supports it.

### Added
- `tests/test_readme_ledger.py`: the required README sections exist and are in order, no marketing word or dash comes back,
  every test the README names exists, the ledger's versions and dates are CHANGELOG headings, the named CI jobs exist, the eight
  Python checks and three README tiers equal the code, the Rust release equals the toolchain file, `STACK.md` does not call CNS
  private, and the worded test-count gap the README lists as open is still open.

### Existing tests edited
- `tests/test_drift.py`: the CNS tag in the fixture pyproject and in the README sentence it asserts (`v1.9.0` to `v2.0.0`, step
  1), and the Warden commit and release strings (`380894f` and 0.13.8 to `b57b81e` and 0.13.9, step 2). Nothing else about the
  tests changed.

## [0.3.10] - 2026-10-22

### Changed
- Warden is re-pinned from `1636e1a21f124eedbf6e158db95dc75344f4308d` (0.13.7) to the full commit
  `380894f0304ef40587dd29efd41b4ceccf94a5d3` (Warden 0.13.8, not tagged). The `Warden.git` spelling and the CNS tag
  `@v1.9.0` are unchanged. The drift-test fixture and the strings it asserts use the new pin.
- `.github/workflows/ci.yml` has a top-level `permissions: contents: read`, so no job runs with the repository's default
  token. The actions stay pinned to full commits, and a new test in `tests/test_release_hygiene.py` fails without the block or
  if a job widens it.
- `burnish critic` on a folder that holds a README and no Python files now exits 2 and says there is nothing to check. It
  exited 0 with "the artifact's story is consistent" for a bare `# hi` README or one that is not UTF-8, a verdict that compared
  the README with nothing, while an empty folder already exited 2. `readme-critic`, `inspect`, `readme`, `cns` and `finish`
  still accept a README with no Python.

### Fixed
- `burnish readme-critic . --tier over-the-top | head -3` ended in a `BrokenPipeError` traceback (exit 1, or exit status 120
  when Python's output is buffered), and the same happened for every command that prints. A closed standard output was a
  silent exit 0 and a full device was a traceback. Now no command ends in a traceback for any of them, `--version` and `--help`
  included. When the reader of a pipe went away, one line on stderr says so and the exit code stays the one the check earned.
  For any other failure to write standard output, one line says why; an earned 1 or 2 is kept and an earned 0 becomes the new
  exit code 3, "the report could not be delivered". The README's exit-code table lists it, and a test keeps the table equal to
  the code.

### Added
- `tests/test_cli_delivery.py` runs each printing command against a closed pipe, a closed descriptor and a full device, in
  a real process with Python's output buffered and unbuffered, plus in-process cases. It fails on the code before this release.

### Existing tests edited
- `tests/test_drift.py`: the Warden commit and release strings (the pin).
- `tests/test_cli_ops.py::test_every_documented_code_is_returned_by_some_run`: it asserts that the documented exit codes are
  exactly the codes some run returns, so it gains the one run that returns the new code 3.
- `tests/test_cli_fail_closed.py::test_critic_and_inspect_accept_a_readme_with_no_python`: its `critic` line now expects exit 2
  instead of 0 or 1, and the test is renamed `test_inspect_accepts_a_readme_with_no_python_and_critic_refuses_it` to stay true.

## [0.3.9] - 2026-10-21

### Changed
- Warden is re-pinned from `0c1ea567f0b69586cfd735f82260774aec9552bb` (0.13.6) to the full commit
  `1636e1a21f124eedbf6e158db95dc75344f4308d` (Warden 0.13.7, not tagged). The `Warden.git` spelling and the CNS tag
  `@v1.9.0` are unchanged. The drift-test fixture and the strings it asserts use the new pin; `tests/test_drift.py` is the
  only existing test file edited, and only for those values.
- The Rust and C++23 CI jobs run on `ubuntu-24.04` instead of `ubuntu-latest`.

### Fixed
- `STACK.md` called CNS private. It is public: an unauthenticated request returns 200 and CI installs it without a token. The
  README never made that claim.
- The C++ gate was described as `g++ -std=c++23 -Wall -Wextra -Wpedantic -Werror` (`burnish languages`) and
  `g++ -std=c++23 -Werror` (README table). CI runs cmake, and `exemplars/cpp23/CMakeLists.txt` sets `CMAKE_CXX_STANDARD 23`
  with `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror`. `burnish languages`, the README table and
  `docs/languages/cpp23.md` now say that, and a new test fails if they stop naming the flags `CMakeLists.txt` sets.

### Added
- `exemplars/rust/rust-toolchain.toml` pins Rust 1.99.0 with clippy and rustfmt, the release the runner image used by the
  last green run ships (from the image manifest; the job log does not print it). The Rust job installs it, prints the
  `rustc`, `cargo` and `clippy` versions, and fails if `rustc` is not that release. `cargo clippy -D warnings` is kept.
  `rust-version = "1.74"` in `Cargo.toml` stays as a declared minimum and is documented as not tested by CI.
- The C++23 job prints the g++ and cmake versions and fails unless the g++ major version is 13 and the cmake major
  version is 3. Only the major version of cmake is asserted because the runner's cmake changed between CI runs (3.28.3,
  then 3.31.6) while the build and its warnings stayed the same.
- "Bumping the toolchain pins" in the README says how to move either pin. Tests in `tests/test_release_hygiene.py` check
  the pins, and one in `tests/test_docs_in_sync.py` checks the C++ flags named in the docs.

## [0.3.8] - 2026-10-21

### Changed
- CNS is re-pinned from the full commit `da18e411743d4e3b0e783105394d845fb1c16746` to its release tag, spelled
  `cns @ git+https://github.com/wking53214/CNS.git@v1.9.0` (the tag peels to that same commit).
- Warden is re-pinned from `decc3c3b5af479ad0eef3df4d66dbcb21e90897c` (0.13.5) to the full commit
  `0c1ea567f0b69586cfd735f82260774aec9552bb` (Warden 0.13.6, not tagged).
- The drift tests use the same pins in their fixture pyproject. The test that checks the git dependencies now expects a
  full commit for Warden and a release tag for CNS.

## [0.3.7] - 2026-10-21

### Changed
- Warden is re-pinned from `36e98433f4928b7d12905f02b56e55ee1943b56e` (0.13.4) to the full commit
  `decc3c3b5af479ad0eef3df4d66dbcb21e90897c` (Warden 0.13.5, not tagged).
- CNS is re-pinned from `5252ceebe98185f7be81212d988055ccf9884568` (v1.8.0) to the full commit
  `da18e411743d4e3b0e783105394d845fb1c16746` (v1.9.0).
- The drift tests use the same Warden and CNS releases and commits in their fixture pyproject.
- `main` (`ef5e4ef`) was already contained in this branch, so no new merge was needed.

## [0.3.6] - 2026-10-21

### Changed
- Warden is re-pinned from `580f659...` (0.13.3) to the full commit `36e98433f4928b7d12905f02b56e55ee1943b56e` (Warden 0.13.4,
  not tagged). Warden still pins CNS to the same commit as Burnish (`5252cee...`, v1.8.0), so `pip install -e ".[dev]"`
  resolves in a fresh environment with `pip check` clean and without `--no-deps`.
- The drift tests use the same Warden release and commit in their fixture pyproject.
- `main` (through `ef5e4ef`, PRs #17 and #18) is merged into this branch. From PR #17: a retired repository named
  `composition-engine` is `NO_ACTION`, not `ADAPTER`, in `cns_boundary`, with its test. PR #18 pinned Warden 0.12.0 and CNS
  `v1.9.0`; this branch keeps the Warden 0.13.4 commit and the CNS v1.8.0 commit that Warden 0.13.4 itself pins, because
  CNS `v1.9.0` conflicts with that Warden pin in a single environment. Both pins stay full commits.

## [0.3.5] - 2026-10-21

### Fixed
- A broken symbolic link with a README name (`README.md` and the other names Burnish looks for) is no longer read as "no
  README". `critic`, `inspect`, `readme`, `cns` and `finish` now exit 2 with "broken symbolic link", as `readme-critic`
  already did. Before, `finish` proposed creating `README.md` over such a link, and a write through a dangling link creates
  its target, possibly outside the repository. `check` reads no README and is unchanged.
- The finisher never proposes an edit whose path is a symbolic link or lies under one, dangling or not, pointing inside or
  outside the folder. It drops the edit and says why in its notes. A README that is a working link was already left alone;
  that is now also guarded for every edit.

## [0.3.4] - 2026-10-21

### Changed
- Warden is re-pinned from `9d9a71d...` (0.13.2) to the full commit `580f659336818b4a5a2c0ca235d2344012536426` (Warden 0.13.3,
  not tagged). Warden still pins CNS to the same commit as Burnish (`5252cee...`, v1.8.0), so `pip install -e ".[dev]"`
  resolves in a fresh environment with `pip check` clean and without `--no-deps`.
- The drift tests use the same Warden release and commit in their fixture pyproject.
- The `[Unreleased]` link is a compare view (from the commit that set the latest version to the head commit) instead of a
  single-commit URL, and a test keeps it one.
- `main`'s change to `burnish/cns_boundary.py` (the retired composition-engine advice) is merged into this branch.

### Fixed
- `critic`, `inspect`, `readme`, `cns` and `finish` skipped a dangling `.py` symbolic link in a tree that also had real files
  and exited 0, while `check` exited 2. They now exit 2 with the reason "broken symbolic link", as `check` does.
- `readme-critic` on a dangling README link said it "found no README to read". It now exits 2 and says "broken symbolic link".

## [0.3.3] - 2026-10-21

### Changed
- Warden is re-pinned from `ec551d8...` (0.13.1) to the full commit `9d9a71d1bc3195f0abd9aee8fe553cc09838b684` (Warden 0.13.2,
  not tagged). Warden still pins CNS to the same commit as Burnish (`5252cee...`, v1.8.0), so `pip install -e ".[dev]"`
  resolves in a fresh environment with `pip check` clean and without `--no-deps`.
- The drift tests use the same Warden release and commit in their fixture pyproject.

## [0.3.2] - 2026-10-17

### Added
- Tests that every GitHub Action in the workflow is pinned to a full commit with its tag in a comment, that the Rust exemplar's
  `Cargo.lock` is tracked and that the Rust job builds with `--locked`.
- A test that the sample output under Usage in the README is exactly what `burnish readme-critic .` prints for this repository.
- A test that `critic`, `readme`, `inspect`, `cns` and `finish` on Python with no README report or generate the README and
  exit 0 (as the README's exit-code section now says).
- Tests that the changelog says no release is tagged without claiming the older `v0.10.0` tag is current, and that its links
  point at commits.

### Changed
- The Rust exemplar's `Cargo.lock` is committed (it was in `.gitignore`), and CI runs `cargo clippy` and `cargo test` with
  `--locked`, so the Rust job is reproducible.
- `actions/checkout` (v4.2.2) and `actions/setup-python` (v5.6.0) are pinned to full commits in CI.
- The README's critic sample is regenerated from the real command on this repository. The old one was output about another
  repository and listed four failures under a headline that said five.
- The changelog no longer says that no release has been tagged yet without mentioning the older `v0.10.0` tag, and its links
  are compare views between commits instead of the branch.

### Fixed
- `burnish check` on a broken symbolic link with a Python name (for example `.py`) still exits 2 and now says "broken symbolic
  link" instead of the error a read of it happened to raise.

## [0.3.1] - 2026-10-17

### Changed
- Warden is re-pinned from `2cf0eec...` (0.12.0) to the full commit `ec551d8e10f82b6e3e681593a97011ae517d360b` (Warden 0.13.1,
  not tagged). Warden now pins CNS to the same commit as Burnish (`5252cee...`, v1.8.0), so `pip install -e ".[dev]"` resolves
  in a fresh environment with `pip check` clean and without `--no-deps`.
- The drift tests use the same Warden release and commit in their fixture pyproject.

## [0.3.0] - 2026-10-17

### Added
- `burnish check`, `critic`, `readme-critic`, `inspect`, `readme`, `finish` and `cns` now fail closed: a path that does not
  exist, is not a folder, holds nothing to read (no Python files, or for `readme-critic` no README) or has a file that
  cannot be read exits 2 with the reason on stderr. They used to print "0 finding(s)" and exit 0.
- The critics check three kinds of README sentence against the tree (`burnish/drift.py`): a "pinned to tag X" claim against
  the ref and release comment in `pyproject.toml`, a "no other dependencies" claim against the declared dependencies and the
  third-party imports, and a stated test count against a collected count. With no collected count (`--collected N` on
  `critic` and `readme-critic`, or Warden's measured suite) a stated test count is reported as unverifiable.
- `readme-critic` exits 1 on any such contradicted claim, at every tier.
- The test-count reader recognises "N test cases" and "N tests are collected".
- Logging to stderr through the standard library: `--verbose` / `-v`, and `BURNISH_LOG_LEVEL`.
- The exit codes (0, 1, 2) are documented in the README and kept equal to the code by a test.
- `ruff` and `mypy` configuration in `pyproject.toml`, both run as CI gates, and Python 3.13 in the CI matrix and classifiers.
- This changelog, and tests that tie `burnish.__version__`, `--version`, the README status line and the newest changelog
  entry to the version in `pyproject.toml`.

### Changed
- CNS is pinned to a full commit (`5252cee...`, release v1.8.0) instead of the `v1.8.0` tag. Warden is still pinned to the
  full commit `2cf0eec...` (0.12.0, not tagged). The release each commit corresponds to is a comment on its line.
- The README no longer restates the Warden pin or a test count, and says which dependencies there are. The pin tests now
  require a full 40-character commit, not a tag, and check that each pin comment names the release that is installed.
- `burnish critic` exits 1 for a README that states a test count and was given no measurement. Wording the count away, or
  passing `--collected`, restores the old result.

### Fixed
- The `mypy` errors (typing gaps in the package and tests) and the `ruff` F401 (unused import) the audit found. One narrow, commented
  `# type: ignore[arg-type]` remains in a test that passes a bare string on purpose.
- A closed output pipe no longer reports "cannot read a file".

## [0.2.0] - 2026-10-08

### Added
- The one-time finisher (`burnish.finisher:Burnish`) that Warden runs after the loop: whitespace tidy and one generated,
  marked README section that never touches the author's words.
- `burnish finish`, `readme`, `cns`, `inspect`, and the README critic with its three tiers (`readme-critic`).

### Changed
- Renamed from Streamline to Burnish.
- Pinned Warden to a commit, then to successive release tags as Warden moved (v0.8.0 to v0.11.x).

### Fixed
- The finisher is a fixed point and edits only between its own markers; it never proposes a change to tests, CI files or
  fixture folders (specimens, golden files, snapshots, a corpus); README test counts are checked against the measured
  suite, with "mentioned, not checked" for counts that belong to something else.

## [0.1.0] - 2026-10-08

### Added
- The criteria as data, the Python checker (eight rules), the README standard and critic, and reference exemplars in
  Python, Rust and C++23 that read one file of test vectors.

[Unreleased]: https://github.com/wking53214/Burnish/compare/118785b14f9b01a64d3d92fef63eb06efa5062d7...118785b14f9b01a64d3d92fef63eb06efa5062d7
[0.3.13]: https://github.com/wking53214/Burnish/compare/2a96c353a5e99de55a99cf6a81d182e7b9afcd78...e9477b85612b48f453be07046d0dd7e63afa86a0
[0.3.12]: https://github.com/wking53214/Burnish/compare/fc9599d2c01fc21aa77626cb8a4f2b2b0b0f77a8...439c4f54ced319512b44ceff5e8a09b650c06ed5
[0.3.11]: https://github.com/wking53214/Burnish/compare/cd09fb49567f9fcf053999233c6ad64da9c6ebe0...801ef9b2897cf35dec94a0c17387a13ad4beccc1
[0.3.10]: https://github.com/wking53214/Burnish/compare/61823a9423a7193e726f5d792f0af50429576474...42d6130df7b8f157e05f0de5dc3c9d9663f2d9aa
[0.3.9]: https://github.com/wking53214/Burnish/compare/9e37d33dd64239ab0702dd23a85afe1add3f4597...815cc0353236f3def816a4ada9434299c1a402e8
[0.3.8]: https://github.com/wking53214/Burnish/compare/befc4291b07c48a18a5bdfddec803144b58f9043...2f1d3eb8dab98050966e33c842e843c6ec70c4b1
[0.3.7]: https://github.com/wking53214/Burnish/compare/2244d9cb6ce2ce1e48f38ff59f7386ef2d194897...a625ec266d214177651acc08122452b3612a559c
[0.3.6]: https://github.com/wking53214/Burnish/compare/72f0681756b14ffaf88249472fb840775c93df75...201c0e660cb9ccbddafbea8af25216d8dc28fb5a
[0.3.5]: https://github.com/wking53214/Burnish/compare/077ce13b93773bbb68bd085b0b33d5b5cb1042f2...5692b33092a79a33b52d08ca7949aa662895ee97
[0.3.4]: https://github.com/wking53214/Burnish/compare/057f3ee90f8c24419cd690f1fcd72c1c886922e6...5a054841b466c7faeb2d3649383f8db9fc74d656
[0.3.3]: https://github.com/wking53214/Burnish/compare/1a3489170a6844a20f41dd92f819026350ccc0f6...ca4235963e022c1df476b7a737de12f05641d945
[0.3.2]: https://github.com/wking53214/Burnish/compare/34a8c8b6fb72a83f531b6d3f7806f996b6fa6316...d708bc83c86206f21ff9735b8fbe82c105b0008c
[0.3.1]: https://github.com/wking53214/Burnish/compare/26b6bda96d849e6d2045cd4f724ed1bb4845d799...34a8c8b6fb72a83f531b6d3f7806f996b6fa6316
[0.3.0]: https://github.com/wking53214/Burnish/compare/7d3a8ead654c45fa5d8fec48fee8dba25e4cb926...26b6bda96d849e6d2045cd4f724ed1bb4845d799
[0.2.0]: https://github.com/wking53214/Burnish/compare/420156d1ec8a3dd98a55f356265370ecb0bcc4c7...7d3a8ead654c45fa5d8fec48fee8dba25e4cb926
[0.1.0]: https://github.com/wking53214/Burnish/commit/420156d1ec8a3dd98a55f356265370ecb0bcc4c7
