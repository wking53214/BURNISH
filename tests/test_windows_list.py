"""The list of tests left out on Windows (in `tests/conftest.py`) names only tests that need Warden, and all the files that do.

Each entry is run in a fresh pytest twice: with Warden blocked, as on Windows, where it must fail, and as installed, where it
must pass. The difference between the two runs is Warden, so that is what the entry needs. (On Windows itself Warden is
blocked in both runs, so there the check shows only that the entry fails.) Every test file that
imports Warden or the finisher at the top must be on the list. The other direction, that no unlisted test needs Warden, is
shown by the Windows CI job, which runs everything else with Warden blocked.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import BLOCK_WARDEN, ON_WINDOWS, WARDEN_ONLY_FILES, WARDEN_ONLY_TESTS

ROOT = Path(__file__).resolve().parent.parent
_NEEDS_WARDEN = ("warden", "burnish.finisher")


def _imports_warden_at_the_top(path: Path) -> bool:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + ([f"{node.module}.{a.name}" for a in node.names] if node.module == "burnish" else [])
        if any(n == m or n.startswith(m + ".") for n in names for m in _NEEDS_WARDEN):
            return True
    return False


def test_every_test_file_that_imports_warden_at_the_top_is_left_out_on_windows():
    found = {p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "tests").glob("test_*.py")) if _imports_warden_at_the_top(p)}
    assert found == set(WARDEN_ONLY_FILES)


def _pytest(entry: str, block_warden: bool) -> tuple[int, str]:
    env = {key: value for key, value in os.environ.items() if key != BLOCK_WARDEN}
    if block_warden:
        env[BLOCK_WARDEN] = "1"
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", entry],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    return done.returncode, done.stdout + done.stderr


@pytest.mark.parametrize("entry", [*WARDEN_ONLY_FILES, *WARDEN_ONLY_TESTS])
def test_each_entry_left_out_on_windows_fails_without_warden_and_passes_with_it(entry: str):
    code, output = _pytest(entry, block_warden=True)
    if code == 0:
        # The delivery tests skip themselves where the system cannot stage the failure; there it is not run at all.
        assert entry.startswith("tests/test_cli_delivery.py::") and " skipped" in output, output
        return
    assert "not found" not in output and "no tests ran" not in output, f"{entry} is not a test that exists:\n{output}"
    if not ON_WINDOWS:
        code, output = _pytest(entry, block_warden=False)
        assert code == 0, f"{entry} fails with Warden installed too, so it is not Warden it lacks:\n{output}"
