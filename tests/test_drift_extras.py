"""A pin or a dependency that pyproject.toml declares only as an optional dependency is not "no such dependency".

Found by running the claims critic over two sibling repositories (round-6 audit, 2026-10-23): SWIZZLE pins CNS in its `cns`
extra and says so in its README, and the critic answered "pyproject.toml pins no git dependency"; ghost_tools declares
`anthropic` in its `semantic` extra and the critic called it "imported but not declared". Both fixtures below are built here
from what those pyproject.toml files contain; nothing is imported from another repository.
"""

from pathlib import Path

import pytest

from burnish import cli
from burnish.critic import PoetryCritic
from burnish.drift import check_tree_claims, claims_held_by_extras

PIN = "cns @ git+https://github.com/example/CNS.git@v2.0.0"

#: Like SWIZZLE: no runtime dependencies, the CNS pin only in the `cns` extra, pytest and ruff in a dev extra and a group.
EXTRAS = f"""[project]
name = "demo"
version = "0.1.0"
description = "demo"
dependencies = []

[project.optional-dependencies]
cns = ["{PIN}"]  # v2.0.0 = b13e5d2f9e0e4291725f82794b89117c3d840ac1
semantic = ["anthropic"]
dev = ["pytest>=8"]

[dependency-groups]
lint = ["ruff==0.15.22"]
test = ["pytest>=8", {{include-group = "lint"}}]
"""

#: Like ghost_tools: `anthropic` imported at the top of a module that only runs with the `semantic` extra.
HARD_IMPORT = '"""demo."""\n\nimport anthropic\n\nVALUE = 1\n'
#: Like SWIZZLE: modules imported inside a function, or guarded by a try that expects the import to fail.
LAZY_IMPORTS = ('"""demo."""\n\n\ndef probe():\n    """Import it when asked."""\n    import warden\n    return warden\n\n\n'
                'try:\n    import pydantic\nexcept ImportError:\n    pydantic = None\n')


def _tree(root: Path, readme: str, pyproject: str = EXTRAS, source: str = HARD_IMPORT) -> Path:
    (root / "demo").mkdir()
    (root / "demo" / "__init__.py").write_text(source, encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


def test_a_pin_that_pyproject_declares_in_an_extra_is_not_a_contradiction(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThe optional CNS connection is pinned to the CNS tag v2.0.0.\n")
    assert check_tree_claims(tmp_path) == []


def test_a_pin_held_only_by_an_extra_is_said_to_be_held_by_an_extra(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThe optional CNS connection is pinned to the CNS tag v2.0.0.\n")
    (held,) = claims_held_by_extras(tmp_path)
    assert held.kind == "pin" and held.verdict == "extra"
    assert "only in an optional dependency" in held.problem and "cns" in held.problem


def test_a_wrong_pin_is_still_a_contradiction_when_the_real_pin_is_in_an_extra(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThe optional CNS connection is pinned to the CNS tag v1.9.0.\n")
    (drift,) = check_tree_claims(tmp_path)
    assert drift.kind == "pin" and drift.verdict == "disagrees"
    assert "pins cns" in drift.problem and "extra cns" in drift.problem and claims_held_by_extras(tmp_path) == []


def test_a_pin_claim_with_no_git_dependency_anywhere_is_still_reported(tmp_path: Path):
    plain = '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n[project.optional-dependencies]\ndev = ["pytest"]\n'
    _tree(tmp_path, "# demo\n\nDemo is pinned to CNS v2.0.0.\n", plain)
    (drift,) = check_tree_claims(tmp_path)
    assert "pins no git dependency" in drift.problem


def test_a_module_declared_in_an_extra_is_not_called_undeclared(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n")
    assert check_tree_claims(tmp_path) == []
    (held,) = claims_held_by_extras(tmp_path)
    assert held.kind == "dependencies" and held.verdict == "extra"
    assert "anthropic" in held.problem and "extra semantic" in held.problem and "not as a runtime dependency" in held.problem


def test_a_module_declared_nowhere_and_imported_at_the_top_is_still_a_contradiction(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", EXTRAS, '"""d."""\n\nimport requests\n')
    (drift,) = check_tree_claims(tmp_path)
    assert "requests (imported in 1 file(s), not declared)" in drift.problem


def test_modules_imported_only_inside_a_function_or_a_guarded_try_are_optional(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", EXTRAS, LAZY_IMPORTS)
    assert check_tree_claims(tmp_path) == []


def test_an_import_under_type_checking_is_not_a_runtime_dependency(tmp_path: Path):
    source = '"""d."""\n\nfrom typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    import numpy\n'
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", EXTRAS, source)
    assert check_tree_claims(tmp_path) == []


def test_a_runtime_dependency_is_still_found_beside_the_extras(tmp_path: Path):
    runtime = EXTRAS.replace("dependencies = []", 'dependencies = ["requests"]')
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", runtime)
    (drift,) = check_tree_claims(tmp_path)
    assert "requests (declared in pyproject.toml" in drift.problem


def test_the_critic_counts_a_claim_held_by_an_extra_as_supported_and_says_why(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThe optional CNS connection is pinned to the CNS tag v2.0.0. There are no runtime dependencies.\n")
    report = PoetryCritic().critique(tmp_path)
    rows = [c for c in report.claims if c.label.startswith("README claim")]
    assert [c.supported for c in rows] == [True, True]
    assert all("optional" in c.note for c in rows)
    assert not any("pinned" in item or "dependencies" in item for item in report.unsupported)


def test_the_readme_critic_command_exits_clean_on_a_claim_held_by_an_extra(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\nThe optional CNS connection is pinned to the CNS tag v2.0.0.\n\n## Install\n\n```bash\npip install .\n```\n")
    cli.main(["readme-critic", str(tmp_path), "--tier", "minimum"])
    assert "Claims the tree contradicts" not in capsys.readouterr().out


def test_dependency_groups_and_extras_are_read_but_do_not_make_a_claim_false(tmp_path: Path):
    """pytest and ruff sit in groups and extras and nothing imports them in the package: no contradiction, no note."""
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", EXTRAS, '"""d."""\n\nVALUE = 1\n')
    assert check_tree_claims(tmp_path) == [] and claims_held_by_extras(tmp_path) == []


def test_the_same_dependency_claim_said_twice_is_reported_once(tmp_path: Path):
    """Round-6 audit: a README that says "no runtime dependencies" and, elsewhere, "no runtime dependency" got two lines."""
    runtime = EXTRAS.replace("dependencies = []", 'dependencies = ["requests"]')
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n\n## Status\n\nIt has no runtime dependency at all.\n", runtime)
    assert len(check_tree_claims(tmp_path)) == 1
    report = PoetryCritic().critique(tmp_path)
    assert [c.label for c in report.claims].count("README claim (dependencies)") == 1
    assert len([item for item in report.unsupported if "requests" in item]) == 1


def test_a_claim_held_by_an_extra_and_said_twice_is_also_reported_once(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n\n## Status\n\nIt has no runtime dependency at all.\n")
    assert len(claims_held_by_extras(tmp_path)) == 1


def test_two_wrong_pin_sentences_with_the_same_complaint_are_reported_once(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nPinned to CNS v1.9.0.\n\n## Install\n\nThe CNS connection is pinned to tag v1.9.0 as well.\n")
    assert len(check_tree_claims(tmp_path)) == 1
