"""Tidying changes whitespace and nothing else, and says nothing when unsure."""

from burnish.beautify import tidy_edits, tidy_source


def test_trailing_whitespace_and_extra_final_newlines_go():
    assert tidy_source("x = 1   \ny = 2\t\n\n\n") == "x = 1\ny = 2\n"


def test_a_file_that_needs_nothing_is_left_alone():
    assert tidy_source("x = 1\n") is None


def test_missing_final_newline_is_added():
    assert tidy_source("x = 1") == "x = 1\n"


def test_trailing_spaces_inside_a_string_are_never_touched():
    source = 'text = """line one   \nline two"""\n'
    assert tidy_source(source) is None


def test_whitespace_outside_the_string_goes_but_inside_stays():
    source = 'y = 1   \ntext = """a  \nb"""\n'
    assert tidy_source(source) == 'y = 1\ntext = """a  \nb"""\n'


def test_unparseable_source_is_not_touched():
    assert tidy_source("def (:   \n") is None


def test_tidy_edits_skips_virtualenvs(tmp_path):
    (tmp_path / "a.py").write_text("x = 1  \n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "b.py").write_text("x = 1  \n", encoding="utf-8")
    assert [e.path for e in tidy_edits(tmp_path)] == ["a.py"]
