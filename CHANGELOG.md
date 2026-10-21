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

[Unreleased]: https://github.com/wking53214/Burnish/compare/61823a9423a7193e726f5d792f0af50429576474...61823a9423a7193e726f5d792f0af50429576474
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
