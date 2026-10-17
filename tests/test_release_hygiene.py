"""One version, said the same way everywhere; a changelog entry for it; pins that are full commits whose comments are true."""

import re
import tomllib
from pathlib import Path

import pytest

import burnish
from burnish import cli

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def test_the_package_version_is_the_pyproject_version():
    assert burnish.__version__ == PYPROJECT["project"]["version"]


def test_version_flag_prints_that_version(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--version"])
    assert stopped.value.code == 0
    assert capsys.readouterr().out.strip() == f"burnish {PYPROJECT['project']['version']}"


def test_the_readme_status_names_the_same_version():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"**Status:** version {PYPROJECT['project']['version']}," in readme


def test_the_changelog_has_an_entry_for_this_version_first():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    versions = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)
    assert versions and versions[0] == PYPROJECT["project"]["version"]
    assert re.search(rf"^\[{re.escape(versions[0])}\]:", changelog, re.M), "the release link is missing"


def test_the_changelog_has_no_unreleased_items_left_behind():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = re.search(r"^## \[Unreleased\]\n(.*?)(?=^## )", changelog, re.M | re.S)
    assert unreleased is None or not unreleased.group(1).strip()


def test_python_313_is_declared_and_tested():
    classifiers = PYPROJECT["project"]["classifiers"]
    assert "Programming Language :: Python :: 3.13" in classifiers
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert '"3.13"' in workflow


def test_every_git_dependency_is_a_full_commit():
    specs = [d for d in PYPROJECT["project"]["dependencies"] if "git+" in d]
    assert len(specs) == 2
    for spec in specs:
        assert FULL_SHA.match(spec.rsplit("@", 1)[1]), f"{spec} is not pinned to a full 40-character commit"


@pytest.mark.parametrize("module,name", [("warden", "Warden"), ("cns", "cns")])
def test_the_release_in_each_pin_comment_is_the_release_installed(module: str, name: str):
    """The comment on a pin's line says which release the commit is; it must match the code that is installed."""
    imported = __import__(module)
    line = next(raw for raw in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines()
                if raw.strip().startswith(f'"{module} @'))
    claimed = re.search(r"#.*?v?(\d+\.\d+\.\d+)", line)
    assert claimed, f"the {name} pin has no release comment"
    assert claimed.group(1) == imported.__version__


WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def test_every_action_is_pinned_to_a_full_commit_with_its_tag_in_a_comment():
    uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)(.*)$", WORKFLOW, re.M)
    assert uses
    for target, rest in uses:
        assert FULL_SHA.match(target.rsplit("@", 1)[1]), f"{target} is not pinned to a full 40-character commit"
        assert re.search(r"#\s*v\d+\.\d+\.\d+", rest), f"{target} has no tag comment"


def test_the_rust_exemplar_lockfile_is_committed_and_ci_builds_with_it_locked():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    assert "Cargo.lock" not in ignored, "Cargo.lock must be tracked so the Rust job is reproducible"
    lock = ROOT / "exemplars" / "rust" / "Cargo.lock"
    assert lock.is_file() and 'name = "defect_ids"' in lock.read_text(encoding="utf-8")
    for command in ("cargo clippy", "cargo test"):
        assert re.search(rf"run: {command} --locked\b", WORKFLOW), f"`{command}` must run with --locked"

