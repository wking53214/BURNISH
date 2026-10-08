"""The three languages Streamline speaks, and how much of each it can enforce.

Each language has a guide in `docs/languages/`, a reference exemplar in
`exemplars/`, and an honest statement of what Streamline checks. Python is
checked by `streamline check`. Rust and C++23 are not: their criteria are
written down and an exemplar follows them, and CI enforces the exemplar with
the language's own tools (clippy and rustfmt for Rust, the compiler with
warnings as errors for C++). Saying so here is the point; a table that
implied otherwise would be the silent pass this project exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass

from elegant.epistemic import EpistemicState

from .criteria import for_scope

__all__ = ["Language", "LANGUAGES", "describe"]


@dataclass(frozen=True)
class Language:
    """One language: its guide, its exemplar, its authority, and how much Streamline enforces."""

    key: str
    name: str
    guide: str
    exemplar: str
    authority: str
    streamline_checks: EpistemicState
    enforced_in_ci_by: str


LANGUAGES: tuple[Language, ...] = (
    Language("python", "Python", "docs/languages/python.md", "exemplars/python",
             "PEP 8 (https://peps.python.org/pep-0008/)", EpistemicState.IMPLEMENTED,
             "streamline check, pytest"),
    Language("rust", "Rust", "docs/languages/rust.md", "exemplars/rust",
             "Rust API Guidelines (https://rust-lang.github.io/api-guidelines/)", EpistemicState.NOT_IMPLEMENTED,
             "cargo fmt --check, cargo clippy -D warnings, cargo test"),
    Language("cpp23", "C++23", "docs/languages/cpp23.md", "exemplars/cpp23",
             "C++ Core Guidelines (https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines)",
             EpistemicState.NOT_IMPLEMENTED, "g++ -std=c++23 -Wall -Wextra -Wpedantic -Werror, ctest"),
)


def describe() -> str:
    """One paragraph per language: what is written, what is checked, and by what."""
    parts = []
    for language in LANGUAGES:
        criteria = for_scope(language.key)
        specific = [c for c in criteria if c.scope == language.key]
        enforced = [c for c in specific if c.state is EpistemicState.IMPLEMENTED]
        parts.append(
            f"{language.name}: {len(specific)} criteria, {len(enforced)} enforced by Streamline "
            f"({language.streamline_checks.value}). Authority: {language.authority}. "
            f"Exemplar: {language.exemplar}. Enforced in CI by: {language.enforced_in_ci_by}.")
    return "\n".join(parts)
