"""The Python checker: each check fires on what it names and stays quiet on clean code."""

from pathlib import Path

from burnish.checks import check_source, check_tree


def _ids(source: str, *, is_test: bool = False) -> set[str]:
    return {f.check for f in check_source(source, "m.py", is_test=is_test)}


CLEAN = '''"""A clean module."""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''


def test_clean_code_has_no_findings():
    assert _ids(CLEAN) == set()


def test_bare_except_is_found():
    assert "PY-EXC" in _ids('"""m."""\ntry:\n    x = 1\nexcept:\n    raise\n')


def test_a_handler_that_only_passes_is_a_swallowed_error():
    assert "PY-SWALLOW" in _ids('"""m."""\ntry:\n    x = 1\nexcept ValueError:\n    pass\n')


def test_a_named_handler_that_acts_is_fine():
    assert _ids('"""m."""\ntry:\n    x = 1\nexcept ValueError:\n    x = 0\n') == set()


def test_wildcard_import_is_found():
    assert "PY-STAR" in _ids('"""m."""\nfrom os.path import *\n')


def test_public_function_without_docstring_is_found():
    assert "PY-DOC" in _ids('"""m."""\n\ndef f(a: int) -> int:\n    x = a\n    return x + 1\n')


def test_private_function_may_go_undocumented():
    assert "PY-DOC" not in _ids('"""m."""\n\ndef _f(a: int) -> int:\n    x = a\n    return x + 1\n')


def test_module_without_docstring_is_found():
    assert "PY-DOC" in _ids("x = 1\n")


def test_bad_names_are_found():
    found = {f.message for f in check_source('"""m."""\n\ndef BadName() -> None:\n    """x."""\n\nclass bad_class:\n    """x."""\n', "m.py")}
    assert any("BadName" in m for m in found) and any("bad_class" in m for m in found)


def test_comparing_to_none_with_equals_is_found():
    assert "PY-CMP" in _ids('"""m."""\nx = 1\ny = x == None\n')
    assert "PY-CMP" in _ids('"""m."""\nx = 1\ny = x != True\n')


def test_is_none_is_fine():
    assert "PY-CMP" not in _ids('"""m."""\nx = 1\ny = x is None\n')


def test_bare_return_beside_a_value_return_is_found():
    source = '"""m."""\n\ndef f(a: int) -> int:\n    """x."""\n    if a:\n        return\n    return 1\n'
    assert "PY-RET" in _ids(source)


def test_explicit_return_none_is_what_pep8_asks_for():
    source = '"""m."""\n\ndef f(a: int) -> "int | None":\n    """x."""\n    if a:\n        return None\n    return 1\n'
    assert "PY-RET" not in _ids(source)


def test_unannotated_public_function_is_found():
    finding = [f for f in check_source('"""m."""\n\ndef f(a):\n    """x."""\n    x = a\n    return x\n', "m.py")
               if f.check == "PY-TYPE"]
    assert finding and "return" in finding[0].message and "a" in finding[0].message


def test_test_files_are_held_to_behavior_but_not_to_docstrings():
    source = "def test_a():\n    try:\n        pass\n    except:\n        pass\n"
    ids = _ids(source, is_test=True)
    assert "PY-EXC" in ids and "PY-DOC" not in ids and "PY-TYPE" not in ids


def test_unparseable_file_is_reported_not_skipped():
    findings = check_source("def (:\n", "broken.py")
    assert [f.check for f in findings] == ["PY-PARSE"]


def test_check_tree_walks_files_and_skips_vendored_directories(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "b.py").write_text("from os import *\n", encoding="utf-8")
    findings = check_tree(tmp_path)
    assert {f.path for f in findings} == {"a.py"}
