"""Streamline is held to everything it holds others to."""

from pathlib import Path

from streamline.checks import check_tree
from streamline.critic import PoetryCritic
from streamline.readme_critic import ReadmeCritic

ROOT = Path(__file__).resolve().parent.parent


def test_streamline_passes_its_own_python_checks():
    findings = check_tree(ROOT)
    assert findings == [], "\n".join(f.render() for f in findings)


def test_streamlines_readme_is_over_the_top_by_its_own_critic():
    report = ReadmeCritic().critique(ROOT)
    assert report.over_the_top, report.as_markdown()


def test_streamlines_documents_tell_the_truth_about_its_tree():
    report = PoetryCritic().critique(ROOT)
    assert report.good_enough, report.as_markdown()
