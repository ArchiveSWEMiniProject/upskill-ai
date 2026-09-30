import pytest

from backend.taxonomy.resolver import (
    AliasConflictError,
    SkillResolver,
    build_alias_index,
    normalise,
)

SKILLS = [(1, "React"), (2, "Python"), (3, "SQL"), (4, "Docker")]
ALIASES = [(1, "ReactJS"), (1, "React.js"), (2, "py"), (3, "PostgreSQL basics")]


@pytest.fixture
def resolver():
    return SkillResolver(build_alias_index(SKILLS, ALIASES))


def test_normalise_lowercases_and_trims():
    assert normalise("  REACT ") == "react"


# TC-F1-08
@pytest.mark.parametrize("variant", ["ReactJS", "React.js", "react", " REACT "])
def test_react_variants_resolve_to_one_skill(resolver, variant):
    assert resolver.resolve(variant) == 1


def test_canonical_name_resolves_to_itself(resolver):
    assert resolver.resolve("Docker") == 4


# TC-F1-09
def test_unknown_string_is_unresolved(resolver):
    assert resolver.resolve("Quantum Blockchain Fabric") is None


def test_empty_and_blank_strings_are_unresolved(resolver):
    assert resolver.resolve("") is None
    assert resolver.resolve("   ") is None


def test_conflicting_alias_is_reported():
    with pytest.raises(AliasConflictError):
        build_alias_index([(1, "React"), (2, "Vue")], [(2, "react")])


def test_same_alias_repeated_for_same_skill_is_fine():
    index = build_alias_index([(1, "React")], [(1, "REACT"), (1, " react ")])
    assert index == {"react": 1}


def test_blank_aliases_are_ignored():
    assert build_alias_index([(1, "React")], [(1, "  ")]) == {"react": 1}


# REQ-F1-05
def test_suggest_returns_closest_canonical_skills(resolver):
    assert resolver.suggest("Pythn")[0] == 2


def test_suggest_has_no_duplicate_skills(resolver):
    result = resolver.suggest("reactj")
    assert result == list(dict.fromkeys(result))
    assert result[0] == 1


def test_suggest_returns_nothing_for_gibberish(resolver):
    assert resolver.suggest("zzzzzzzz") == []
