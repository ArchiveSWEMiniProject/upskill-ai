"""Skill string resolver (M1).

Maps free-text skill strings to canonical skill ids using the alias table from
the frozen taxonomy schema (docs/CONTRACTS.md, section 2). Matching is done on
a lowercased, whitespace-trimmed form (REQ-F1-20, F1-21).

Pure logic with no database access: callers load skills and aliases through
M4's interface and build the index with build_alias_index().
"""

from collections.abc import Iterable, Mapping
from difflib import get_close_matches


class AliasConflictError(ValueError):
    """Two different skills claim the same normalised alias: a taxonomy data error."""


def normalise(text: str) -> str:
    """Lowercase and trim, the form stored in skill_alias.alias_text."""
    return text.strip().lower()


def build_alias_index(
    skills: Iterable[tuple[int, str]],
    aliases: Iterable[tuple[int, str]] = (),
) -> dict[str, int]:
    """Build a normalised-text -> skill_id index.

    `skills` is (skill_id, skill_name) pairs and `aliases` is
    (skill_id, alias_text) pairs. A canonical name always resolves to itself.
    """
    index: dict[str, int] = {}
    for skill_id, text in [*skills, *aliases]:
        key = normalise(text)
        if not key:
            continue
        if index.setdefault(key, skill_id) != skill_id:
            raise AliasConflictError(
                f"'{key}' maps to both skill {index[key]} and skill {skill_id}"
            )
    return index


class SkillResolver:
    def __init__(self, alias_index: Mapping[str, int]):
        self._index = dict(alias_index)

    def resolve(self, text: str) -> int | None:
        """Return the canonical skill_id, or None if the string is unresolved."""
        return self._index.get(normalise(text))

    def suggest(self, text: str, limit: int = 3) -> list[int]:
        """Closest canonical skill ids for an unknown string (REQ-F1-05).

        Ordered best match first, with each skill_id appearing once.
        """
        keys = get_close_matches(normalise(text), self._index, n=limit * 3, cutoff=0.6)
        seen: list[int] = []
        for key in keys:
            skill_id = self._index[key]
            if skill_id not in seen:
                seen.append(skill_id)
        return seen[:limit]
