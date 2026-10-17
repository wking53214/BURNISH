# Changelog

All notable changes to Burnish are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). No release has been tagged yet; the links
below point at commits and at the working branch until the owner tags one.

## [Unreleased]

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

[Unreleased]: https://github.com/wking53214/Burnish/commits/claude/horsemen-production-status-5wsndb
[0.3.0]: https://github.com/wking53214/Burnish/commits/claude/horsemen-production-status-5wsndb
[0.2.0]: https://github.com/wking53214/Burnish/commit/7d3a8ea
[0.1.0]: https://github.com/wking53214/Burnish/commit/420156d
