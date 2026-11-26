"""Every command but `finish` runs without Warden installed (item 31 of the remediation plan, 0.5.0).

Burnish left the circuit on 2026-10-29; what is still used are the standalone checkers, and they never needed Warden. The
command-line tool loaded the finisher at start, so before 0.5.0 every command, even `--version`, failed with
ModuleNotFoundError when Warden was missing. Each test runs a fresh Python in which importing Warden fails.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: Python with Warden blocked: `import warden` raises ImportError, as when it is not installed.
_RUN = ("import sys; sys.modules['warden'] = None; from burnish import cli; "
        "sys.exit(cli.main(sys.argv[1:]))")


def _burnish(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", _RUN, *args], capture_output=True, text=True, cwd=ROOT, timeout=120)


@pytest.mark.parametrize("args", [("--version",), ("check", "burnish"), ("critic", "."), ("readme-critic", "."),
                                  ("inspect", "."), ("readme", "."), ("cns", "."), ("criteria",), ("languages",)],
                         ids=lambda args: args[0])
def test_a_standalone_command_runs_without_warden(args: tuple[str, ...]):
    done = _burnish(*args)
    assert "warden" not in done.stderr.lower(), done.stderr
    assert done.returncode == 0, (done.returncode, done.stderr[-2000:])


def test_finish_without_warden_says_what_is_missing_and_exits_2():
    done = _burnish("finish", ".")
    assert done.returncode == 2, done.stderr
    assert "needs Warden, which is not installed" in done.stderr and "burnish[finisher]" in done.stderr
    assert "Traceback" not in done.stderr


def test_warden_is_the_finisher_extra_and_not_a_runtime_dependency():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not any(d.startswith("warden") for d in project["dependencies"])
    assert [d.split(" @")[0] for d in project["optional-dependencies"]["finisher"]] == ["warden"]
    assert "burnish[finisher]" in project["optional-dependencies"]["dev"], "the suite tests the finisher, so dev needs it"


def test_only_the_finisher_imports_warden():
    importers = sorted(path.name for path in (ROOT / "burnish").glob("*.py")
                       if any(line.lstrip().startswith(("import warden", "from warden"))
                              for line in path.read_text(encoding="utf-8").splitlines()))
    assert importers == ["finisher.py"]


def test_the_readme_role_section_names_warden_as_the_finisher_extra():
    """0.5.0 moved Warden to the `finisher` extra; the role section said otherwise until 0.5.1."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    (line,) = [raw for raw in readme.splitlines() if raw.startswith("- **Depends on.**")]
    assert "CNS" in line and "`finisher` extra" in line and not line.startswith("- **Depends on.** Warden")
