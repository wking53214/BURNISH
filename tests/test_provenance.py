"""Every finding of the claims critic says where it comes from, so a reviewer can repeat it (2026-11-25, item 10 of the plan).

Each row carries the claim, the file and line of the claim and of each piece of evidence, the method, whether the evidence
is direct or inferred, what was not inspected, and the reason for the verdict. These tests check that every field is there
for every kind of finding, and that each line it names really holds what it says: the test opens the file at that line.
"""

from pathlib import Path

import pytest

from cns.seat import Facts
from cns.suite import SuiteRun

from burnish.critic import TREE_FINDINGS, Claim, PoetryCritic
from burnish.marked import BEGIN, END
from burnish.provenance import Provenance, Source
from burnish.readme import compile_readme
from burnish.narrative import inspect_tree

GIT_PIN = 'cns @ git+https://github.com/wking53214/CNS.git@v2.0.0'


def _tree(root: Path, readme: str, pyproject: str | None = None, files: dict[str, str] | None = None) -> Path:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text('"""owns nothing declared."""\n', encoding="utf-8")
    for name, text in (files or {}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    if pyproject is not None:
        (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


def _line(root: Path, source: Source) -> str:
    """The line a source points at, as a reviewer would open it."""
    assert source.path and source.line > 0, source
    return (root / source.path).read_text(encoding="utf-8").splitlines()[source.line - 1]


def _row(claims: tuple[Claim, ...], kind: str) -> Claim:
    (row,) = [c for c in claims if c.kind == kind]
    return row


def _complete(p: Provenance | None) -> Provenance:
    """Every one of the six fields is there and says something."""
    assert p is not None
    assert p.claim and p.method and p.reason and p.not_inspected and all(p.not_inspected)
    assert p.basis in ("direct", "inferred", "none")
    assert p.basis == "none" or p.evidence, "evidence is named whenever the verdict rests on some"
    return p


# ---- pin

def test_a_pin_finding_names_the_readme_line_and_the_pyproject_line(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nIntro.\n\nCNS is pinned to v1.0.0 here.\n",
                 f'[project]\nname = "demo"\nversion = "1"\ndependencies = [\n  "{GIT_PIN}",\n]\n')
    report = PoetryCritic().critique(root)
    row = _row(report.claims, "pin")
    p = _complete(row.provenance)
    assert row.agreement == "disagrees" and p.reason == row.note
    assert "pinned to v1.0.0" in _line(root, p.claim_at) and p.claim_at.path == "README.md"
    (evidence,) = p.evidence
    assert evidence.path == "pyproject.toml" and GIT_PIN in _line(root, evidence)
    assert p.basis == "direct", "the sentence names CNS, so the pin it means is not a guess"
    assert any("no tag or commit was fetched" in item for item in p.not_inspected)


def test_a_pin_sentence_that_names_no_dependency_is_inferred(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nIt is pinned to v1.0.0.\n",
                 f'[project]\nname = "demo"\nversion = "1"\ndependencies = ["{GIT_PIN}"]\n')
    p = _complete(_row(PoetryCritic().critique(root).claims, "pin").provenance)
    assert p.basis == "inferred" and "compared with every pin" in p.method


def test_a_pin_with_no_git_dependency_points_at_the_whole_file(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nIt is pinned to v1.0.0.\n", '[project]\nname = "demo"\nversion = "1"\n')
    p = _complete(_row(PoetryCritic().critique(root).claims, "pin").provenance)
    assert p.evidence == (Source("pyproject.toml", 0, p.evidence[0].what),) and "no git dependency" in p.evidence[0].what


def test_a_pin_held_by_an_extra_carries_provenance_too(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nCNS is pinned to v2.0.0.\n",
                 f'[project]\nname = "demo"\nversion = "1"\n\n[project.optional-dependencies]\ndev = ["{GIT_PIN}"]\n')
    row = _row(PoetryCritic().critique(root).claims, "pin")
    p = _complete(row.provenance)
    assert row.supported and "extra" in p.reason and GIT_PIN in _line(root, p.evidence[0])


# ---- dependencies

def test_an_undeclared_import_is_inferred_and_points_at_the_import(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n",
                 '[project]\nname = "demo"\nversion = "1"\ndependencies = []\n',
                 {"pkg/use.py": '"""uses requests."""\n\nimport os\nimport requests\n'})
    row = _row(PoetryCritic().critique(root).claims, "dependencies")
    p = _complete(row.provenance)
    assert row.agreement == "disagrees"
    assert "no runtime dependencies" in _line(root, p.claim_at)
    (evidence,) = p.evidence
    assert evidence.path == "pkg/use.py" and _line(root, evidence) == "import requests"
    assert p.basis == "inferred", "the package is known only through the module's name"


def test_a_declared_dependency_is_direct_and_points_at_its_declaration(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n",
                 '[project]\nname = "demo"\nversion = "1"\ndependencies = [\n  "attrs>=23",\n]\n')
    p = _complete(_row(PoetryCritic().critique(root).claims, "dependencies").provenance)
    assert p.basis == "direct" and '"attrs>=23"' in _line(root, p.evidence[0])


def test_an_import_inside_a_function_is_unconfirmed_and_says_what_was_not_checked(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n",
                 '[project]\nname = "demo"\nversion = "1"\ndependencies = []\n',
                 {"pkg/late.py": '"""late."""\n\n\ndef f():\n    import yaml\n    return yaml\n'})
    row = _row(PoetryCritic().critique(root).claims, "dependencies")
    p = _complete(row.provenance)
    assert row.agreement == "unconfirmed" and p.basis == "inferred"
    assert _line(root, p.evidence[0]).strip() == "import yaml" and "inside a function" in p.evidence[0].what
    assert any("runs on every use" in item for item in p.not_inspected)


def test_a_file_that_does_not_parse_is_named_as_not_read_for_imports(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n",
                 '[project]\nname = "demo"\nversion = "1"\ndependencies = []\n',
                 {"pkg/use.py": "import requests\n", "pkg/bad.py": "def (:\n"})
    p = _complete(_row(PoetryCritic().critique(root).claims, "dependencies").provenance)
    assert any("could not be parsed: pkg/bad.py" in item for item in p.not_inspected)


# ---- test counts

def test_an_unmeasured_count_says_there_was_no_evidence(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nAll 16 tests pass.\n", '[project]\nname = "demo"\nversion = "1"\n')
    row = _row(PoetryCritic().critique(root).claims, "tests")
    p = _complete(row.provenance)
    assert row.agreement == "unmeasured" and p.basis == "none" and p.evidence == ()
    assert "All 16 tests pass" in _line(root, p.claim_at)


def test_a_count_judged_against_warden_names_the_suite_result_as_its_evidence(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nAll 16 tests pass.\n", '[project]\nname = "demo"\nversion = "1"\n')
    facts = Facts(suite=SuiteRun(ran=True, passed=5), remaining=(), cycles=1)
    row = _row(PoetryCritic().critique(root, facts=facts).claims, "tests")
    p = _complete(row.provenance)
    assert row.agreement == "disagrees" and p.basis == "direct"
    (evidence,) = p.evidence
    assert evidence.path == "" and "Warden" in evidence.what and p.reason == row.note


def test_a_count_against_collected_names_the_collected_count(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nThe suite has 16 tests.\n", '[project]\nname = "demo"\nversion = "1"\n')
    report = PoetryCritic().critique(root, collected=9)
    (row,) = [c for c in report.claims if c.kind == "tests" and c.agreement == "disagrees"]
    p = _complete(row.provenance)
    assert p.basis == "direct" and "--collected (9)" in p.evidence[0].what
    assert any("a count, not a result" in item for item in p.not_inspected)


def test_an_unverifiable_passing_count_keeps_one_row_with_the_collected_evidence(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nAll 16 tests pass.\n", '[project]\nname = "demo"\nversion = "1"\n')
    row = _row(PoetryCritic().critique(root, collected=16).claims, "tests")
    p = _complete(row.provenance)
    assert row.agreement == "unmeasured" and "--collected (16)" in p.evidence[0].what
    assert "whether they pass was not measured" in p.reason


# ---- broken metadata

def test_a_broken_pyproject_names_the_line_the_parser_stopped_at(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n",
                 '[project]\nname = "demo"\nversion = = "1"\n')
    report = PoetryCritic().critique(root)
    meta = _complete(_row(report.claims, "metadata").provenance)
    assert meta.evidence[0].path == "pyproject.toml" and _line(root, meta.evidence[0]) == 'version = = "1"'
    assert meta.basis == "direct" and any("every pin and dependency" in item for item in meta.not_inspected)
    claim = _row(report.claims, "dependencies")
    p = _complete(claim.provenance)
    assert claim.agreement == "unchecked" and p.evidence == meta.evidence
    assert "no runtime dependencies" in _line(root, p.claim_at)


# ---- parse failure

def test_a_parse_failure_names_the_file_and_the_line_the_parser_stopped_at(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n", None, {"pkg/bad.py": '"""bad."""\n\nx = 1\ndef (:\n'})
    report = PoetryCritic().critique(root)
    row = _row(report.claims, "parse")
    p = _complete(row.provenance)
    assert report.outcome.value == "FAIL" and p.basis == "direct"
    (evidence,) = p.evidence
    assert evidence.path == "pkg/bad.py" and _line(root, evidence) == "def (:" and "SyntaxError" in evidence.what


# ---- the other findings

def test_an_absolute_claim_names_its_line_and_has_no_evidence(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nIntro.\n\nIt is production ready.\n")
    p = _complete(_row(PoetryCritic().critique(root).claims, "absolute").provenance)
    assert p.basis == "none" and "production ready" in _line(root, p.claim_at)


def test_a_cns_mention_points_at_the_line_that_mentions_it(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n", None, {"pkg/seam.py": '"""seam."""\n\nfrom cns.seat import Facts\n'})
    p = _complete(_row(PoetryCritic().critique(root).claims, "cns").provenance)
    assert _line(root, p.evidence[0]) == "from cns.seat import Facts"


def test_a_brochure_readme_points_at_the_word_that_made_it_one(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nA tool.\n\nIt is powerful.\n")
    report = PoetryCritic().critique(root)
    note = next(n for n in report.what_is_ugly if "brochure" in n)
    assert "line 5" in note and '"powerful"' in note


def test_a_red_suite_is_a_row_with_the_suite_result_as_evidence(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n")
    facts = Facts(suite=SuiteRun(ran=True, passed=3, failed=1), remaining=(), cycles=0)
    p = _complete(_row(PoetryCritic().critique(root, facts=facts).claims, "suite").provenance)
    assert p.basis == "direct" and "Warden" in p.evidence[0].what


def test_a_living_readme_on_a_retired_tree_points_at_both_files(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\n## Usage\n\npip install demo\n\nIt does not do much.\n", None,
                 {"PROVENANCE.md": "# Provenance\n\nThis design was retired in 2025.\n"})
    p = _complete(_row(PoetryCritic().critique(root).claims, "history").provenance)
    readme, provenance = p.evidence
    assert "pip install" in _line(root, readme) and "retired" in _line(root, provenance)


# ---- across every kind

CASES = {
    "pin": ("CNS is pinned to v1.0.0.\n", f'[project]\nname = "d"\nversion = "1"\ndependencies = ["{GIT_PIN}"]\n', {}),
    "dependencies": ("No runtime dependencies.\n", '[project]\nname = "d"\nversion = "1"\n', {"pkg/u.py": "import requests\n"}),
    "tests": ("All 16 tests pass.\n", None, {}),
    "metadata": ("Intro.\n", '[project\n', {}),
    "parse": ("Intro.\n", None, {"pkg/bad.py": "def (:\n"}),
}


@pytest.mark.parametrize("kind", sorted(CASES))
def test_every_row_has_all_six_fields_and_the_report_prints_them(tmp_path: Path, kind: str):
    prose, pyproject, files = CASES[kind]
    root = _tree(tmp_path, "# demo\n\n" + prose, pyproject, files)
    report = PoetryCritic().critique(root)
    assert any(c.kind == kind for c in report.claims)
    for row in report.claims:
        _complete(row.provenance)
    printed = report.as_markdown()
    for label in ("Claim:", "Evidence:", "Method:", "Evidence is:", "Not inspected:", "Reason:"):
        assert printed.count(f"  - {label} ") == len(report.claims), label


def test_a_line_number_is_the_files_own_after_a_generated_block_and_crlf_line_ends(tmp_path: Path):
    """The critic reads the README with LF line ends and its own block removed; the line it reports is the file's."""
    readme = ("# demo\r\n\r\nIntro.\r\n\r\n" + BEGIN + "\r\n## Measured facts (generated)\r\n\r\n- a\r\n- b\r\n" + END
              + "\r\n\r\n```\r\ncode\r\n```\r\n\r\nIt is pinned to v1.0.0.\r\n")
    root = _tree(tmp_path, "", f'[project]\nname = "d"\nversion = "1"\ndependencies = ["{GIT_PIN}"]\n')
    (root / "README.md").write_bytes(readme.encode("utf-8"))
    p = _complete(_row(PoetryCritic().critique(root).claims, "pin").provenance)
    assert p.claim_at.line == 16 and "pinned to v1.0.0" in readme.split("\r\n")[15]


def test_findings_about_the_tree_stay_out_of_the_generated_readme_section(tmp_path: Path):
    root = _tree(tmp_path, "# demo\n\nAll 16 tests pass.\n", '[project\n', {"pkg/bad.py": "def (:\n"})
    report = PoetryCritic().critique(root)
    assert {"metadata", "parse"} <= {c.kind for c in report.claims} <= TREE_FINDINGS | {"tests"}
    section = compile_readme(inspect_tree(root), report)
    assert "can be parsed" not in section and "pyproject.toml can be read" not in section
    assert "count 16" in section
