"""UP-7: finding skills in resume text (pure function, no database)."""

from decimal import Decimal

from backend.profile.skill_extraction import (
    CEILING,
    MAX_SENTENCE_CHARS,
    extract_candidates,
    split_sentences,
)
from backend.taxonomy.resolver import build_alias_index

PYTHON, REACT, SQL, POSTGRES, CPP, ML = 1, 2, 3, 4, 5, 6
INDEX = build_alias_index(
    [(PYTHON, "Python"), (REACT, "React"), (SQL, "SQL"), (POSTGRES, "PostgreSQL"),
     (CPP, "C++"), (ML, "Machine Learning")],
    [(REACT, "react.js"), (REACT, "reactjs"), (PYTHON, "python3"), (ML, "ml")],
)


def by_skill(text: str) -> dict:
    return {c.skill_id: c for c in extract_candidates(text, INDEX)}


def test_sentences_split_on_lines_and_full_stops():
    assert split_sentences("One.  Two!\n\nThree\nfour?") == ["One.", "Two!", "Three", "four?"]


def test_names_and_aliases_resolve_to_one_canonical_skill_each():
    found = by_skill("Built a dashboard in React.js. Also used ReactJS and react at work.")
    assert set(found) == {REACT}


def test_matching_is_whole_word_so_sql_is_not_found_inside_postgresql():
    found = by_skill("Designed schemas in PostgreSQL.")
    assert set(found) == {POSTGRES}


def test_a_longer_name_hides_a_shorter_one_inside_it():
    index = build_alias_index([(1, "Machine Learning"), (2, "Learning")])
    found = {c.skill_id for c in extract_candidates("Studied machine learning.", index)}
    assert found == {1}


def test_names_ending_in_symbols_are_found():
    assert set(by_skill("Wrote a ray tracer in C++.")) == {CPP}
    assert by_skill("Grade C in maths") == {}


def test_every_candidate_carries_its_source_sentence():
    text = "Asha Rao\nSkills: Python, SQL\nInterned at a bank working on ML models."
    found = by_skill(text)
    assert found[PYTHON].source_sentence == "Skills: Python, SQL"
    assert found[ML].source_sentence == "Interned at a bank working on ML models."


def test_level_follows_the_words_around_the_skill():
    found = by_skill(
        "Expert in Python.\nBuilt a React app.\nC++ coursework."
    )
    assert found[PYTHON].level == "advanced"
    assert found[REACT].level == "intermediate"
    assert found[CPP].level == "beginner"


def test_a_skills_list_and_a_level_word_raise_confidence():
    plain = by_skill("C++ coursework.")[CPP].confidence
    listed = by_skill("Skills: C++")[CPP].confidence
    stated = by_skill("Skills: advanced C++")[CPP].confidence
    assert plain < listed < stated


def test_repeated_mentions_raise_confidence_but_never_to_certainty():
    once = by_skill("Python scripts.")[PYTHON].confidence
    many = by_skill(
        "Skills: expert Python.\nPython.\nPython.\nPython.\nPython.\nPython."
    )[PYTHON].confidence
    assert once < many <= CEILING < Decimal("1.00")


def test_confidence_has_two_decimal_places_and_is_in_range():
    for candidate in extract_candidates("Skills: Python, React, SQL. Built with C++.", INDEX):
        assert candidate.confidence == candidate.confidence.quantize(Decimal("0.01"))
        assert Decimal("0") <= candidate.confidence <= CEILING


def test_strongest_first_and_one_per_skill():
    candidates = extract_candidates("Python.\nSkills: React, Python", INDEX)
    assert [c.skill_id for c in candidates] == [PYTHON, REACT]
    assert candidates[0].source_sentence == "Skills: React, Python"


def test_long_sentences_are_cut_for_display():
    candidate = extract_candidates("Python " + "word " * 200, INDEX)[0]
    assert len(candidate.source_sentence) == MAX_SENTENCE_CHARS


def test_text_without_known_skills_gives_nothing():
    assert extract_candidates("Enjoys hiking and chess.", INDEX) == []
    assert extract_candidates("", INDEX) == []
