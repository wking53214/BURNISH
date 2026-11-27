"""On Windows, the tests that need Warden are left out by name (items 27 and 28 of the remediation plan, 0.5.10).

Warden, which only `finish` needs, locks files with `fcntl`, which exists on Linux and macOS and not on Windows, so on Windows
Warden cannot be imported and `finish` cannot run. Every other command runs there. The owner chose to run everything else on
Windows and leave these out by name here, not with skip markers. `tests/test_windows_list.py` holds the list honest: each
entry fails when Warden is blocked, and every test file that imports Warden or the finisher at the top is on it. The Windows
CI job runs the rest with Warden blocked, so a test that needs Warden and is not listed fails there, on every push.

On Windows, Warden is blocked outright (`import warden` raises ImportError) so the result does not depend on the order the
files are collected in: a half-finished import of Warden can otherwise let a later import appear to work.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ON_WINDOWS = sys.platform == "win32"

#: Test files that import Warden or the finisher at the top, so nothing in them can be collected without Warden.
WARDEN_ONLY_FILES = (
    "tests/test_block_has_no_snapshots.py",
    "tests/test_finisher.py",
    "tests/test_no_edit_through_a_link.py",
    "tests/test_second_red_team.py",
    "tests/test_stable_and_careful.py",
)

#: Single tests that need Warden, in files whose other tests do not.
WARDEN_ONLY_TESTS = (
    "tests/test_critic.py::test_what_ghost_still_reports_is_named_as_ugly",
    "tests/test_cli_delivery.py::test_a_full_device_cannot_leave_a_lost_report_at_exit_0[finish-write]",
    "tests/test_cli_delivery.py::test_a_full_device_cannot_leave_a_lost_report_at_exit_0[finish-flush]",
    "tests/test_cli_delivery.py::test_a_closed_standard_output_cannot_leave_a_lost_report_at_exit_0[finish]",
    "tests/test_cli_fail_closed.py::test_the_other_commands_still_read_a_readme_with_no_python[finish]",
    "tests/test_cli_fail_closed.py::test_python_with_no_readme_is_reported_not_refused[finish]",
    "tests/test_release_hygiene.py::test_the_release_in_each_pin_comment_is_the_release_installed[warden-Warden]",
    "tests/test_small_fixes.py::test_check_and_finish_both_name_a_file_that_is_too_deep",
    "tests/test_undecodable_file.py::test_finish_still_says_not_valid_utf8_for_the_same_file",
    "tests/test_warden_pin.py::test_burnish_declares_the_contract_of_the_warden_it_is_pinned_to",
)

#: Set by `tests/test_windows_list.py` to block Warden on any system without leaving anything out.
BLOCK_WARDEN = "BURNISH_TEST_BLOCK_WARDEN"

if ON_WINDOWS or os.environ.get(BLOCK_WARDEN) == "1":
    sys.modules["warden"] = None  # type: ignore[assignment]

collect_ignore = [Path(name).name for name in WARDEN_ONLY_FILES] if ON_WINDOWS else []


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not ON_WINDOWS:
        return
    left_out = [item for item in items if item.nodeid in WARDEN_ONLY_TESTS]
    if left_out:
        config.hook.pytest_deselected(items=left_out)
        items[:] = [item for item in items if item.nodeid not in WARDEN_ONLY_TESTS]
