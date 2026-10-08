# Streamline

What makes code beautiful, written down, checked, and applied to itself.

[![CI](https://github.com/wking53214/Streamline/actions/workflows/ci.yml/badge.svg)](https://github.com/wking53214/Streamline/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

[Install](#install) | [Usage](#usage) | [Architecture](#architecture) | [Languages](#languages) | [FAQ](#faq) | [Design](docs/DESIGN.md) | [Criteria](docs/CRITERIA.md) | [README standard](docs/README_STANDARD.md)

**Status:** version 0.2.0, alpha, maintained by one person. The Python checker, the README critic and the finisher work. The finisher tidies whitespace and writes the final README; the rewrites for names, comments and guards are designed and **not built**; see [What it does not do](#what-it-does-not-do).

## What this is

Streamline is the home of the beautification criteria: naming as truth,
narrative documentation, architectural properties as comments, the rewriting
rules, best practices for Python, Rust and C++23, and the standard for a README
that is over the top. It also holds the tools that measure a tree against those
criteria and say, bluntly, where it falls short.

It is the finisher: it runs once, after the loop of Ghost Tools, Proposer, Elegant and SWIZZLE has converged. It tidies the code and writes the final README, including the critic's commentary. It still never writes a file itself. It returns a proposal, and [Elegant](https://github.com/wking53214/Elegant) applies it, which needs a named human and a green test suite first, and puts it back if the suite breaks or Ghost finds anything new.

## Why it exists

Beautifying code is easy to do badly. The original rules lived inside Elegant,
mixed with the discipline of change, and in one edit the detailed text of the
principles and rules 1 to 6 was cut down to headings. The opinion about what
better code is deserved its own repository, with its full text restored, so it
could be judged, improved and applied to itself.

## Install

```bash
pip install git+https://github.com/wking53214/Streamline.git
```

This also installs [Elegant](https://github.com/wking53214/Elegant), which
Streamline plugs into. Python 3.11 or newer. No other dependencies.

To work on it:

```bash
git clone https://github.com/wking53214/Streamline.git
cd Streamline
pip install -e ".[dev]"
pytest
```

## Usage

Ask for a blunt review of any repository's README:

```bash
streamline readme-critic path/to/repo
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
streamline check path/to/repo
```

```text
risky.py:4: PY-TYPE: `risky` has no annotation for: path, return
risky.py:8: PY-EXC: bare `except:` catches everything, including KeyboardInterrupt; name the exceptions
risky.py:8: PY-SWALLOW: the handler only passes, so a failure looks like success; handle it or let it rise
streamline check: 3 finding(s) (PY-EXC 1, PY-SWALLOW 1, PY-TYPE 1)
```

That output is also real, from a four-line demo file with a bare `except` that
passes. The exit code is 1 when anything is found.

The other commands:

| Command | What it does |
|---------|--------------|
| `streamline critic PATH` | Reads the README and modules against what the tree declares. Exit 1 on "This isn't good enough yet." |
| `streamline inspect PATH` | What the tree declares about itself, as JSON |
| `streamline readme PATH` | Prints a README draft compiled from the tree. Never writes |
| `streamline finish PATH` | Lists the files the finishing proposal would change. Never writes |
| `streamline cns PATH` | A recommendation about a repository's CNS seam. Never modifies CNS |
| `streamline criteria` | Every criterion, its level, and how implemented it is |
| `streamline languages` | What is written down and what is enforced, per language |

To finish a repository, hand Streamline to Elegant as the finisher. Nothing
is written without `--authorize`:

```bash
elegant tagteam path/to/repo --proposer proposer.seat:Proposer --finisher streamline.finisher:Streamline --ghost-root ../ghost_tools --swizzle-root ../SWIZZLE
```

## Architecture

```text
criteria.py          the rules, as data
   │
   ├── checks.py          Python rules a program can judge
   ├── readme_critic.py   README rules, in three tiers
   └── critic.py          the critic's commentary on measured facts
                              │
narrative.py  reads the tree  │
beautify.py   tidies Python source, behavior-preserving
readme.py     compiles and finalizes the README
finisher.py   the one proposal Elegant asks for, once, after the loop
```

Invariants, each enforced by a test:

- No Streamline module writes or deletes a file.
- No Streamline module counts tests or imports another role (Proposer, Ghost Tools, SWIZZLE, TOUCHSTONE). What it says about the suite or about defects, it quotes from the facts Elegant hands it.
- Nothing is called `IMPLEMENTED` unless Streamline enforces it, and nothing is called enforced for Rust or C++23.
- Streamline passes its own Python checks and its own README critic at the over-the-top tier.
- The criteria table and the documents cannot disagree.

The reasoning, the analogy behind the design, and what was rejected are in
[docs/DESIGN.md](docs/DESIGN.md).

## Languages

| Language | Authority | Streamline checks it | Exemplar | Enforced in CI by |
|----------|-----------|----------------------|----------|-------------------|
| Python | [PEP 8](https://peps.python.org/pep-0008/) | **Yes**, eight rules | [exemplars/python](exemplars/python) | `streamline check`, `pytest` |
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

**Can it fix my code?** Not by itself. Fixing is the Proposer's job, inside the loop. Streamline runs once, after the loop, and proposes a tidy and the final README. Elegant, with a human grant and a green suite, decides. Today the tidy removes trailing whitespace and nothing else.

**Why does it check Python but not Rust or C++?** Because only Python has a
checker. Rust and C++23 have written criteria and a working exemplar, and the
language's own tools enforce the exemplar in CI. `streamline languages` says so.

**Why is the critic so harsh?** Because a critic that praises is a brochure. The
README critic is allowed, and required, to say a README is not good.

## What it does not do

WHAT IT DOES NOT OWN:

- Writing to a repository. That is Elegant's, behind a human grant.
- The test gate, the SWIZZLE proof gate and the audit file. Also Elegant's.
- Forensic detection of long functions, dead code and duplicates, and counting tests. That is ghost_tools.
- Proposing fixes inside the loop. That is Proposer.
- Renaming, narrative comments, inline architectural comments, guards and function splits. They are designed (`PA`, `PB`, `PC`, `R1` to `R4`) and have no rewriter.
- Checking Rust or C++23 code.
- Judging whether prose is clear or an image is good, fetching URLs, or telling a dead external link.
- Scoring anything.

## Alternatives

Formatters and linters such as ruff, black, clippy and clang-tidy enforce
style on one language and should be used alongside this. READMEs have templates
and spec checkers such as Standard Readme. Streamline differs in two ways: it
keeps the criteria, the languages and the README standard in one place that
checks itself, and it separates the opinion about better code from the
authority to change it.

## Evidence

CI runs the Python tests on 3.11 and 3.12, runs Streamline on itself, builds the
Rust exemplar with clippy and rustfmt, and builds the C++23 exemplar with GCC and
warnings as errors.

91 tests exist in this tree. They are Python `test_*` functions; the
Rust and C++ exemplars have their own checks under `ctest` and `cargo test`.

## Claims versus reality

Here is what the artifact says it is: the home of the beautification criteria,
with tools that measure code against them and say so bluntly.

Here is what we can establish: the checker, the README critic and the critic
of claims run, are tested, and pass on this tree. The three exemplars build and
agree on the same vectors.

Here is where those disagree: the criteria describe far more than is enforced.
Of the Python criteria, eight are checked. Of the Rust and C++23 criteria, none are
checked by Streamline. Most of the craft practices need a person. Counting the
whole table, the share marked `IMPLEMENTED` is small, and `streamline criteria`
prints exactly which. Clang 18 with libstdc++ 13 cannot build the C++ exemplar;
only GCC was verified. The research behind the guides has gaps, listed in
[docs/RESEARCH.md](docs/RESEARCH.md).

## Roadmap

Outstanding, in the order a person would likely want them:

1. A first rewrite for names or comments in the finisher, behind Elegant's gate.
2. Read the parts of the C++ Core Guidelines the first pass missed, and add their criteria.
3. A Rust checker, if Clippy's lints are not enough.
4. Run Elegant's loop with Proposer and Streamline in their seats on a real repository and record it in Elegant's registry.

## Support

Open an [issue](https://github.com/wking53214/Streamline/issues) for questions
or bugs.

## Contributing

Issues and pull requests are welcome. Run `pytest` and `streamline check .`
first; both must pass, and the README critic must still say the README is over
the top. A change to a criterion changes `streamline/criteria.py` and the page
that describes it in the same pull request, or the docs-in-sync test fails.

## Design analogy

Streamline is a style editor beside a safety inspector. The editor knows what
good writing looks like and marks it up; the inspector decides whether the
building may be changed at all and checks it afterwards. In operational terms,
Streamline reviews and proposes and Elegant authorizes, gates and records. The
full table of vibecode, plain language and operational terms is in
[docs/DESIGN.md](docs/DESIGN.md).

## License

Apache-2.0. Copyright 2026 William N. King. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
