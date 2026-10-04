import dataclasses
import json
from decimal import Decimal

import pytest

from backend.shared.skill_vector import (
    InvalidSkillVectorError,
    Level,
    ProfileNotFoundError,
    SharedError,
    SkillVector,
    SkillVectorEntry,
    Source,
)


def entry(skill_id=1, **overrides):
    fields = {
        "canonical_skill_id": skill_id,
        "canonical_skill_name": "Python",
        "level": Level.beginner,
        "confidence": None,
        "source": Source.manual,
    }
    fields.update(overrides)
    return SkillVectorEntry(**fields)


# --- Level -----------------------------------------------------------------


def test_level_value_is_the_contract_string():
    assert json.dumps(Level.beginner) == '"beginner"'
    assert Level("advanced") is Level.advanced


def test_level_rank_orders_beginner_intermediate_advanced():
    assert [level.rank for level in Level] == [0, 1, 2]
    assert Level.beginner < Level.intermediate < Level.advanced
    assert Level.advanced > Level.intermediate > Level.beginner
    assert Level.beginner <= Level.beginner
    assert Level.advanced >= Level.advanced
    assert sorted([Level.advanced, Level.beginner, Level.intermediate]) == [
        Level.beginner,
        Level.intermediate,
        Level.advanced,
    ]


@pytest.mark.parametrize("compare", [
    lambda: Level.beginner < 1,
    lambda: Level.beginner <= 1,
    lambda: Level.beginner > 1,
    lambda: Level.beginner >= 1,
])
def test_level_refuses_comparison_with_non_levels(compare):
    with pytest.raises(TypeError):
        compare()


# --- SkillVectorEntry ------------------------------------------------------


def test_entry_accepts_valid_values():
    result = entry(level=Level.advanced, confidence=0.9, source=Source.resume)
    assert result.level is Level.advanced
    assert result.source is Source.resume
    assert result.confidence == Decimal("0.90")


def test_entry_coerces_exact_strings_to_enums():
    result = entry(level="advanced", source="resume")
    assert result.level is Level.advanced
    assert result.source is Source.resume


@pytest.mark.parametrize("overrides", [
    {"level": "expert"},
    {"level": "Beginner"},
    {"source": "typo"},
    {"confidence": 7.5},
    {"confidence": -0.1},
    {"confidence": float("nan")},
    {"confidence": "0.5"},
    {"confidence": True},
    {"canonical_skill_name": "x" * 61},
    {"canonical_skill_name": "   "},
    {"canonical_skill_name": 5},
    {"canonical_skill_id": "1"},
    {"canonical_skill_id": True},
])
def test_entry_rejects_contract_violations(overrides):
    with pytest.raises(InvalidSkillVectorError):
        entry(**overrides)


def test_entry_allows_a_name_of_exactly_60_characters():
    assert len(entry(canonical_skill_name="x" * 60).canonical_skill_name) == 60


@pytest.mark.parametrize(("given", "stored"), [
    (0, "0.00"),
    (1, "1.00"),
    (0.8, "0.80"),
    (0.875, "0.88"),
    (Decimal("0.5"), "0.50"),
])
def test_confidence_is_stored_as_two_decimal_places(given, stored):
    assert entry(confidence=given).confidence == Decimal(stored)


def test_manual_skill_may_have_no_confidence():
    assert entry(confidence=None).confidence is None


def test_entry_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry().level = Level.advanced


# --- SkillVector -----------------------------------------------------------


def test_vector_sorts_entries_by_skill_id_for_deterministic_output():
    vector = SkillVector([entry(3), entry(1), entry(2)])
    assert [item.canonical_skill_id for item in vector] == [1, 2, 3]


def test_vector_lookup_and_membership():
    vector = SkillVector([entry(1), entry(3)])
    assert len(vector) == 2
    assert 3 in vector
    assert 2 not in vector
    assert vector.get(1).canonical_skill_id == 1
    assert vector.get(9) is None


def test_empty_vector_is_valid():
    assert len(SkillVector()) == 0


def test_vector_rejects_the_same_skill_twice():
    with pytest.raises(InvalidSkillVectorError):
        SkillVector([entry(1), entry(1, level=Level.advanced)])


def test_vector_rejects_items_that_are_not_entries():
    with pytest.raises(InvalidSkillVectorError):
        SkillVector([("not", "an entry")])


# --- Exceptions ------------------------------------------------------------


def test_invalid_vector_error_is_a_value_error_and_a_shared_error():
    error = InvalidSkillVectorError("bad")
    assert isinstance(error, ValueError)
    assert isinstance(error, SharedError)


def test_profile_not_found_carries_the_student_id():
    error = ProfileNotFoundError(5)
    assert isinstance(error, SharedError)
    assert error.student_id == 5
    assert "5" in str(error)
