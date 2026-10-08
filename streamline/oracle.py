"""The documentation-honesty oracle: independent of the critic, reading only the tree.

The critic reviews. The oracle attacks. They are separate on purpose, and
`tests/test_independence.py` proves it: neither module imports the other, so
a flattering review cannot launder a bad change, and a harsh one cannot hide
a good change.

The oracle freezes what is true of the tree *before* a change (test count,
module count, a hash of the README) and re-measures after. It does not read
the proposal to decide whether the proposal was right.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from elegant.craft import AttackResult

from .narrative import inspect_tree


@dataclass(frozen=True)
class GroundTruth:
    """Frozen before anything Elegant writes."""

    test_functions: int
    module_count: int
    readme_sha16: str
    execute_present: bool

    @property
    def fingerprint(self) -> str:
        """What Elegant records as the baseline: a short hash of the README as frozen."""
        return self.readme_sha16


def freeze(root: Path) -> GroundTruth:
    """Record what is true of the tree before a change."""
    nar = inspect_tree(root)
    readme = Path(nar.root) / "README.md"
    blob = readme.read_bytes() if readme.is_file() else b""
    execute_present = any("execute" in m.functions or "execute" in m.classes for m in nar.modules)
    for m in nar.modules:
        if m.path.endswith("pipeline.py") and "execute" in (m.purpose + "".join(m.functions)):
            execute_present = True
    return GroundTruth(
        test_functions=nar.test_functions,
        module_count=len(nar.modules),
        readme_sha16=hashlib.sha256(blob).hexdigest()[:16],
        execute_present=execute_present,
    )


def attack_documentation_honesty(root: Path, before: GroundTruth) -> AttackResult:
    """Independent of Elegant's critic. Re-counts the tree. Rejects a README
    that claims a test count the tree does not have.
    """
    after = inspect_tree(root)
    violations = []
    if after.test_functions != before.test_functions:
        # A documentation-only transform must not change the test suite.
        # If tests changed, this attack cannot attribute the README.
        return AttackResult(
            judgement="INCONCLUSIVE",
            violations=(),
            notes=(
                f"test_* count moved {before.test_functions} → {after.test_functions}; "
                "documentation-honesty oracle will not speak"
            ),
        )
    for phrase, n in after.test_count_claims():
        if n != after.test_functions:
            violations.append(
                f"README/PROVENANCE still claims {n} via {phrase!r}; "
                f"tree has {after.test_functions} test_* functions"
            )
    if violations:
        return AttackResult("REJECT", tuple(violations), "documentation honesty failed")
    return AttackResult("ACCEPT", (), "no false test-count claims remain")
