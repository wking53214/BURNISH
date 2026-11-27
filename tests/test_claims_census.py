"""Campaign 2, part 2: the census of claim-like sentences no check reads, so silence is visible.

The 0.5.11 Warden miss had one root cause: the README said "the program needs Warden", no check had that shape, and the
report said nothing about the sentence. These tests hold the census to its job: every present-tense sentence that sounds
like a claim of a known class and that no check read is listed, with its line; history, wishes, rules, quotations and
reported speech are not; and the list changes no outcome.
"""

from __future__ import annotations

from pathlib import Path

from burnish.claims import ABSOLUTES
from burnish.critic import Outcome, PoetryCritic
from burnish.verify.census import claim_like

ROOT = Path(__file__).resolve().parent.parent

#: A README of claims nothing in Burnish checked before the census, one per line pair, and the classes each should get.
SILENT = {
    "Demo works on Python 3.9 or newer.": ("python-version",),
    "Runs on Linux, macOS and Windows.": ("platform",),
    "Windows is not supported.": ("platform",),
    "It is fast: it starts in under 50 ms.": ("performance",),
    "It is secure by design.": ("security",),
    "It is fully compatible with the 0.x API.": ("compatibility",),
    "All features are complete.": ("feature-completion",),
    "Deploys to AWS Lambda with one command.": ("build-deploy",),
    "It has 80% branch coverage.": ("coverage",),
    "It is fast and secure.": ("performance", "security"),
}

#: Sentences that look like those claims and make none now.
NOT_CLAIMS = [
    "Before 0.3, demo ran on Python 3.8.",                   # history
    "We plan to support Python 3.14.",                       # a wish
    "It should run on Windows one day.",                     # a wish
    "The old README claimed it runs on Python 3.7.",        # reported speech
    'An old note read "secure and fast".',                   # a quotation
    "See SECURITY.md for the security policy.",              # a mention with no claim verb
]


def _tree(tmp_path: Path, readme: str) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "1"\ndependencies = []\n'
                                             '[project.scripts]\ndemo = "demo.cli:run"\n', encoding="utf-8")
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "__init__.py").write_text('"""Demo."""\n', encoding="utf-8")
    (tmp_path / "demo" / "cli.py").write_text('"""Cli."""\n\n\ndef run():\n    return 0\n', encoding="utf-8")
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    return tmp_path


def _readme(sentences: list[str]) -> str:
    return "# demo\n\n" + "\n\n".join(sentences) + "\n"


# ---------------------------------------------------------------- the stage on its own

def test_each_class_of_claim_is_found_with_its_line():
    text = _readme(list(SILENT))
    got = {m.words: m.kinds for m in claim_like(text)}
    assert got == SILENT
    lines = [m.line for m in claim_like(text)]
    assert lines == list(range(3, 3 + 2 * len(SILENT), 2))


def test_history_wishes_quotations_reported_speech_and_bare_mentions_are_not_claims():
    assert claim_like(_readme(NOT_CLAIMS)) == []


def test_headings_and_code_are_not_read():
    text = "# Fast and secure\n\n```\nit runs on Windows\n```\n\n    It is secure.\n"
    assert claim_like(text) == []


def test_a_sentence_over_two_lines_spans_both():
    (mention,) = claim_like("# demo\n\nIt runs on\nWindows and Linux.\n\nNext one has nothing.\n")
    assert (mention.line, mention.end) == (3, 4)


# ---------------------------------------------------------------- in the critic

def test_the_critic_lists_every_unread_claim_and_still_passes(tmp_path: Path):
    report = PoetryCritic().critique(_tree(tmp_path, _readme(list(SILENT))))
    assert report.outcome is Outcome.PASS   # the census changes no outcome
    assert [m.words for m in report.unread] == list(SILENT)
    text = report.as_markdown()
    assert "## Claim-like, not read" in text
    assert '- python-version: "Demo works on Python 3.9 or newer." (README.md line 3)' in text


def test_a_sentence_a_check_read_is_not_listed_for_that_class(tmp_path: Path):
    readme = _readme(["It has 100% coverage.", "It is 100% secure and fast."])
    report = PoetryCritic().critique(_tree(tmp_path, readme))
    assert [r.kind for r in report.claims] == ["absolute", "absolute"]
    # coverage and security were read as absolutes; the speed claim beside them was not read by anything
    assert [(m.words, m.kinds) for m in report.unread] == [("It is 100% secure and fast.", ("performance",))]


def test_a_report_with_nothing_unread_has_no_census_section(tmp_path: Path):
    report = PoetryCritic().critique(_tree(tmp_path, _readme(["Demo prints a greeting."])))
    assert report.unread == ()
    assert "Claim-like, not read" not in report.as_markdown()


def test_burnish_own_python_and_platform_claim_is_visible_and_changes_nothing():
    report = PoetryCritic().critique(ROOT)
    assert report.outcome is Outcome.PASS
    hit = [m for m in report.unread if "CI runs 3.11, 3.12 and 3.13 on Linux, Windows and macOS" in m.words]
    assert hit and {"python-version", "platform"} <= set(hit[0].kinds)


# ---------------------------------------------------------------- the trail names what it matched

def test_the_absolute_method_names_every_phrase_it_matches(tmp_path: Path):
    report = PoetryCritic().critique(_tree(tmp_path, _readme(["It is production ready."])))
    (row,) = [r for r in report.claims if r.kind == "absolute"]
    assert row.provenance is not None
    assert all(phrase in row.provenance.method for phrase in ABSOLUTES)
