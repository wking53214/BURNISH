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
        ref = spec.rsplit("@", 1)[1]
        if spec.startswith("cns @"):
            assert re.fullmatch(r"v\d+\.\d+\.\d+", ref), f"{spec} is not pinned to a release tag"
        else:
            assert FULL_SHA.match(ref), f"{spec} is not pinned to a full 40-character commit"


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


def test_the_docs_do_not_say_that_no_release_is_tagged_when_an_older_tag_exists():
    for name in ("README.md", "CHANGELOG.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "No release has been tagged yet" not in text, name
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "v0.10.0" in changelog and "not tagged yet" in changelog and "owner" in changelog


def test_the_changelog_links_point_at_commits_not_at_a_branch():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    links = re.findall(r"^\[[^\]]+\]: (\S+)$", changelog, re.M)
    assert links
    for link in links:
        assert "/commits/" not in link and "claude/" not in link, f"{link} points at a branch"
        assert re.search(r"/(commit|compare)/", link), link


def test_the_unreleased_link_is_a_compare_view_between_two_full_commits():
    """Not a single-commit URL: [Unreleased] shows what changed from a commit to a commit."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    link = re.search(r"^\[Unreleased\]: (\S+)$", changelog, re.M)
    assert link, "the [Unreleased] link is missing"
    assert re.fullmatch(r"https://github\.com/wking53214/Burnish/compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40}", link.group(1)), link.group(1)


TOOLCHAIN = tomllib.loads((ROOT / "exemplars" / "rust" / "rust-toolchain.toml").read_text(encoding="utf-8"))["toolchain"]
CARGO = tomllib.loads((ROOT / "exemplars" / "rust" / "Cargo.toml").read_text(encoding="utf-8"))["package"]


def _release(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _job(name: str) -> str:
    block = re.search(rf"^  {name}:\n(.*?)(?=^  \w[\w-]*:\n|\Z)", WORKFLOW, re.M | re.S)
    assert block, f"no {name} job"
    return block.group(1)


def test_the_rust_toolchain_is_one_exact_release_with_the_tools_ci_runs():
    assert re.fullmatch(r"\d+\.\d+\.\d+", TOOLCHAIN["channel"]), "name a release such as 1.99.0, not stable or a range"
    assert {"clippy", "rustfmt"} <= set(TOOLCHAIN["components"])


def test_the_declared_rust_minimum_is_not_above_the_pinned_toolchain():
    assert _release(CARGO["rust-version"]) <= _release(TOOLCHAIN["channel"])


def test_the_rust_job_installs_the_pinned_toolchain_and_asserts_it_before_linting():
    job = _job("rust")
    assert re.search(r"^\s*- run: rustup toolchain install$", job, re.M)
    assert "rust-toolchain.toml" in job and "rustc --version" in job and "cargo clippy --version" in job
    assert job.index("rustup toolchain install") < job.index("rustc --version") < job.index("cargo clippy --locked")
    assert "-D warnings" in job


def test_the_rust_and_cpp_jobs_run_on_a_named_image_not_the_moving_latest():
    for name in ("rust", "cpp23"):
        runs_on = re.search(r"^    runs-on: (\S+)$", _job(name), re.M)
        assert runs_on and re.fullmatch(r"ubuntu-\d\d\.\d\d", runs_on.group(1)), name


def test_the_cpp_job_prints_and_asserts_the_compiler_and_cmake_versions_before_building():
    job = _job("cpp23")
    assert re.search(r'^\s+GXX_MAJOR: "\d+"$', job, re.M) and re.search(r'^\s+CMAKE_MAJOR: "\d+"$', job, re.M)
    for tool in ('"g++-${GXX_MAJOR}" --version', "cmake --version", "-dumpversion", '= "${GXX_MAJOR}"', '= "${CMAKE_MAJOR}"'):
        assert tool in job, tool
    assert job.index("-dumpversion") < job.index("cmake -S")
