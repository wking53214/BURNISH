"""The documents and the code say the same thing, or this fails."""

import re
from pathlib import Path

from warden.epistemic import EpistemicState

from burnish.checks import CHECK_IDS, check_tree
from burnish.criteria import CRITERIA, Level, by_id, for_scope
from burnish.languages import LANGUAGES
from burnish.readme_critic import RULES

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def _all_docs_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in DOCS.rglob("*.md"))


def test_every_criterion_is_written_up_in_the_docs():
    text = _all_docs_text()
    missing = [c.id for c in CRITERIA if not re.search(rf"(?<![A-Za-z0-9-]){re.escape(c.id)}(?![A-Za-z0-9-])", text)]
    assert missing == []


def test_every_readme_rule_appears_in_the_readme_standard():
    text = (DOCS / "README_STANDARD.md").read_text(encoding="utf-8")
    assert [r.id for r in RULES if f"`{r.id}`" not in text] == []


def test_criterion_ids_are_unique():
    ids = [c.id for c in CRITERIA]
    assert len(ids) == len(set(ids))


def test_by_id_names_the_missing_id():
    try:
        by_id("NOPE")
    except KeyError as error:
        assert "NOPE" in str(error)
    else:
        raise AssertionError("expected a KeyError")


def test_a_check_named_by_a_criterion_exists():
    known = set(CHECK_IDS) | {r.id for r in RULES}
    assert [c.id for c in CRITERIA if c.check and c.check not in known] == []


def test_a_python_criterion_marked_implemented_has_a_check():
    implemented = [c for c in for_scope("python") if c.scope == "python" and c.state is EpistemicState.IMPLEMENTED]
    assert implemented and all(c.check in CHECK_IDS for c in implemented)


def test_nothing_is_marked_implemented_for_a_language_burnish_does_not_check():
    for language in ("rust", "cpp23"):
        assert not [c for c in CRITERIA if c.scope == language and c.state is EpistemicState.IMPLEMENTED]


def test_every_language_has_a_guide_and_an_exemplar():
    for language in LANGUAGES:
        assert (ROOT / language.guide).is_file(), language.guide
        assert (ROOT / language.exemplar).is_dir(), language.exemplar
    assert (ROOT / "exemplars" / "vectors.txt").is_file()


def test_the_python_exemplar_passes_the_python_checker():
    assert check_tree(ROOT / "exemplars" / "python") == []


def test_only_human_judgement_is_claimed_for_what_a_program_cannot_judge():
    human = [c for c in CRITERIA if c.level is Level.HUMAN]
    assert human and all(c.check is None for c in human)
