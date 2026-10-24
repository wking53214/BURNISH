"""A test count written the way people write it: a thousands separator, a k, a number word.

Round-6 audit: "1.374 tests pass" was not read as a count of 1374 (a dot between thousands is how many languages write it),
"1 374 tests pass" was read as 374 (the first group was dropped), and "1k tests pass" and "twelve tests pass" were not
detected at all, so a README could state a count the critics never saw.
"""

import pytest

from burnish.claims import test_claims as read_claims
from burnish.drift import check_test_claims


def _one(sentence: str):
    found = read_claims(f"# demo\n\n{sentence}\n")
    assert len(found) == 1, (sentence, found)
    return found[0]


@pytest.mark.parametrize("sentence", [
    "1,374 tests pass.", "1.374 tests pass.", "1 374 tests pass.", "1 374 tests pass.", "1 374 tests pass.",
    "1'374 tests pass.", "1_374 tests pass.", "The suite has 1.374 tests.", "All 1.374 tests passed.", "1.374 passing tests.",
])
def test_a_thousands_separator_of_any_common_kind_gives_the_whole_number(sentence: str):
    assert _one(sentence).number == 1374


@pytest.mark.parametrize("sentence,number", [
    ("30 000 tests passed.", 30000), ("12 374 tests pass.", 12374), ("1.374.000 tests pass.", 1374000),
    ("1.374/1.374 passing.", 1374),
])
def test_larger_numbers_and_a_ratio_keep_every_group(sentence: str, number: int):
    assert _one(sentence).number == number


@pytest.mark.parametrize("sentence,number", [
    ("1k tests pass.", 1000), ("1.4k tests pass.", 1400), ("12K tests passed.", 12000), ("The suite has 2k tests.", 2000),
])
def test_a_k_means_a_thousand(sentence: str, number: int):
    assert _one(sentence).number == number


@pytest.mark.parametrize("sentence,number", [
    ("twelve tests pass.", 12), ("Twenty-one tests pass.", 21), ("ninety tests pass.", 90), ("Forty two tests pass.", 42),
    ("two hundred tests pass.", 200), ("A hundred tests pass.", 100), ("one hundred and five tests pass.", 105),
    ("The suite has seventeen tests.", 17),
])
def test_a_number_word_is_a_count(sentence: str, number: int):
    assert _one(sentence).number == number


@pytest.mark.parametrize("sentence", [
    "Runs under Python 3.11 tests pass on CI.", "Tested on Python 3.11 tests included.", "Version 2.0.0 tests are in tests/.",
    "No one tests the parser.", "Someone tests it by hand.", "We added twelve tests for the parser.",
    "Before the fix, ten tests failed.", "It went from two hundred to three hundred tests.",
])
def test_the_new_forms_do_not_turn_other_sentences_into_claims(sentence: str):
    assert read_claims(f"# demo\n\n{sentence}\n") == []


def test_a_worded_count_is_reported_as_unverifiable_like_any_other():
    (drift,) = check_test_claims("# demo\n\nNinety tests pass.\n")
    assert drift.verdict == "unverifiable" and "count of 90" in drift.problem


def test_a_dotted_count_is_judged_against_a_collected_number():
    assert check_test_claims("# demo\n\n1.374 tests pass.\n", collected=1374) == []
    (drift,) = check_test_claims("# demo\n\nThe suite has 1.374 tests.\n", collected=1200)
    assert "count of 1374" in drift.problem


@pytest.mark.parametrize("sentence", [
    "About a thousand tests pass.", "A couple of hundred tests pass.", "1.5 million tests pass.",
    "One thousand three hundred and seventy four tests pass.",
])
def test_wordier_counts_are_still_missed_and_never_misread_as_a_smaller_number(sentence: str):
    """A known defect, held as an assertion (the README lists it): no claim is read, and above all not the tail "374"."""
    assert read_claims(f"# demo\n\n{sentence}\n") == []
