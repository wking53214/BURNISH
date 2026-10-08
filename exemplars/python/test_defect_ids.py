"""The Python exemplar against the shared vectors, plus the rules the vectors cannot say."""

from pathlib import Path

import pytest

from defect_ids import Allocator, DefectId, ParseError, Priority, parse

VECTORS = Path(__file__).resolve().parent.parent / "vectors.txt"


def _vectors(kind: str) -> list[list[str]]:
    rows = []
    for line in VECTORS.read_text(encoding="utf-8").splitlines():
        words = line.split()
        if words and not line.startswith("#") and words[0] == kind:
            rows.append([("" if w == "<empty>" else w) for w in words[1:]])
    return rows


def _ids(field: str) -> list[str]:
    return [] if field == "-" else field.split(",")


@pytest.mark.parametrize("row", _vectors("parse"), ids=lambda r: r[0] or "<empty>")
def test_parse_matches_the_vectors(row):
    text, verdict, expected = row
    if verdict == "ok":
        assert str(parse(text)) == expected
    else:
        with pytest.raises(ParseError) as raised:
            parse(text)
        assert raised.value.kind == expected


@pytest.mark.parametrize("row", _vectors("alloc"), ids=lambda r: f"{r[0]}-{r[1]}")
def test_alloc_matches_the_vectors(row):
    existing, priority, verdict, expected = row
    if verdict == "ok":
        assert str(Allocator(_ids(existing)).allocate(Priority(priority))) == expected
    else:
        with pytest.raises(ParseError) as raised:
            Allocator(_ids(existing))
        assert raised.value.kind == expected


@pytest.mark.parametrize("row", _vectors("seq"), ids=lambda r: r[0] + "-" + r[1])
def test_sequences_match_the_vectors(row):
    existing, priorities, _, expected = row
    allocator = Allocator(_ids(existing))
    assert [str(allocator.allocate(Priority(p))) for p in priorities.split(",")] == expected.split(",")


def test_ids_order_by_priority_then_number():
    assert parse("C9") < parse("H1") < parse("M1") < parse("L1")
    assert parse("H2") < parse("H10")


def test_an_id_cannot_be_built_with_a_zero_number():
    with pytest.raises(ParseError):
        DefectId(Priority.HIGH, 0)
