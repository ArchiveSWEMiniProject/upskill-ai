"""Skill extraction from resume text (UP-7, REQ-F1-12 to F1-14).

extract_candidates() is a pure function: it gets the resume's text and the
taxonomy's alias index and returns one candidate per canonical skill found,
with a suggested level, a confidence and the sentence it was found in. It
stores nothing; candidates are only proposals until the student confirms them
(UP-8, REQ-F1-15).

How it works, kept deliberately simple and deterministic:

- The text is split into sentences (lines and sentence-ending punctuation).
- Every canonical name and alias is looked for as a whole word, ignoring
  case, so "React.js" and "react" both find React, but "SQL" is not found
  inside "PostgreSQL" (that one is found only if PostgreSQL is in the
  taxonomy itself). Longer names win over shorter ones that overlap them.
- Level comes from words in the same sentence ("expert", "advanced" give
  advanced; "intermediate", "experienced", "built" and similar give
  intermediate); otherwise beginner.
- Confidence starts at BASE and rises when the sentence looks like a skills
  list or states a level, and when the skill is mentioned more than once. It
  never reaches 1.00, because text alone cannot prove a skill is held.

For each skill the strongest sentence is kept (highest confidence, then the
first one in the resume).
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from backend.taxonomy.resolver import normalise

BASE = Decimal("0.50")
SKILLS_SECTION_BONUS = Decimal("0.20")
LEVEL_WORD_BONUS = Decimal("0.10")
REPEAT_BONUS = Decimal("0.05")  # per extra sentence mentioning the skill
MAX_REPEAT_BONUS = Decimal("0.15")
CEILING = Decimal("0.95")
MAX_SENTENCE_CHARS = 300

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")
_SKILLS_HEADING = re.compile(r"\b(skills?|technolog(y|ies)|tools|tech stack|proficien\w*)\b", re.I)
_ADVANCED = re.compile(r"\b(expert|advanced|extensive|proficient|mastery|strong)\b", re.I)
_INTERMEDIATE = re.compile(
    r"\b(intermediate|experienced|experience|built|developed|implemented|designed|"
    r"deployed|worked (?:with|on)|used)\b",
    re.I,
)


@dataclass(frozen=True)
class Candidate:
    skill_id: int
    level: str  # beginner | intermediate | advanced
    confidence: Decimal  # 0.00 to 0.95, two decimal places
    source_sentence: str


def split_sentences(text: str) -> list[str]:
    parts = (" ".join(part.split()) for part in _SENTENCE_END.split(text))
    return [part for part in parts if part]


def _pattern(alias: str) -> re.Pattern[str]:
    # Whole-word match that also works for names ending in symbols ("c++", "c#").
    return re.compile(rf"(?<![\w+#.]){re.escape(alias)}(?![\w+#])", re.I)


def _level(sentence: str) -> str:
    if _ADVANCED.search(sentence):
        return "advanced"
    if _INTERMEDIATE.search(sentence):
        return "intermediate"
    return "beginner"


def _found_in(sentence: str, patterns: list[tuple[re.Pattern[str], int]]) -> set[int]:
    """Skill ids named in the sentence; a longer match hides shorter ones inside it."""
    taken: list[tuple[int, int]] = []
    found: set[int] = set()
    for pattern, skill_id in patterns:  # longest alias first
        for match in pattern.finditer(sentence):
            start, end = match.span()
            if any(start < t_end and t_start < end for t_start, t_end in taken):
                continue
            taken.append((start, end))
            found.add(skill_id)
    return found


def extract_candidates(text: str, alias_index: Mapping[str, int]) -> list[Candidate]:
    """One candidate per canonical skill named in `text`, strongest first.

    `alias_index` maps normalised names and aliases to skill ids, as built by
    backend.taxonomy.resolver.build_alias_index."""
    patterns = [
        (_pattern(alias), skill_id)
        for alias, skill_id in sorted(alias_index.items(), key=lambda item: -len(item[0]))
        if normalise(alias)
    ]
    mentions: dict[int, list[str]] = {}
    for sentence in split_sentences(text):
        for skill_id in _found_in(sentence, patterns):
            mentions.setdefault(skill_id, []).append(sentence)

    candidates = []
    for skill_id, sentences in mentions.items():
        repeat = min(REPEAT_BONUS * (len(sentences) - 1), MAX_REPEAT_BONUS)
        best: tuple[Decimal, str] | None = None
        for sentence in sentences:
            score = BASE + repeat
            if _SKILLS_HEADING.search(sentence):
                score += SKILLS_SECTION_BONUS
            if _ADVANCED.search(sentence) or _INTERMEDIATE.search(sentence):
                score += LEVEL_WORD_BONUS
            score = min(score, CEILING).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if best is None or score > best[0]:
                best = (score, sentence)
        confidence, sentence = best
        candidates.append(
            Candidate(skill_id, _level(sentence), confidence, sentence[:MAX_SENTENCE_CHARS])
        )
    candidates.sort(key=lambda c: (-c.confidence, c.skill_id))
    return candidates
