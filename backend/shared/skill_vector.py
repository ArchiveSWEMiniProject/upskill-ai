"""
backend/shared/skill_vector.py

Shared, frozen-contract types for the skill vector (section 1 of
docs/CONTRACTS.md). Changing anything here requires all four of us to agree
(rule R3).

Owner: M1 (Vansh), the producer of the skill vector. Consumers (M2, M3)
import from here; nobody defines their own copy. Only M1 writes a vector
(rule R4); the merge rules (highest level wins, both sources recorded,
raise-only updates) are M1 logic and are not implemented here.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

NAME_MAX_LENGTH = 60
_TWO_PLACES = Decimal("0.01")


class SharedError(Exception):
    """Base class for errors raised through the shared contracts."""


class InvalidSkillVectorError(SharedError, ValueError):
    """A skill vector entry or vector breaks the frozen contract."""


class ProfileNotFoundError(SharedError):
    """get_skill_vector() was called for a student with no profile."""

    def __init__(self, student_id: int | str):
        super().__init__(f"No profile exists for student {student_id}")
        self.student_id = student_id


class Level(StrEnum):
    """beginner < intermediate < advanced.

    The value is the string stored in the database and sent over the API.
    Comparisons use rank, never the string.
    """

    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"

    @property
    def rank(self) -> int:
        return _LEVEL_RANK[self]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Level):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Level):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Level):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Level):
            return NotImplemented
        return self.rank >= other.rank


_LEVEL_RANK = {Level.beginner: 0, Level.intermediate: 1, Level.advanced: 2}


class Source(StrEnum):
    manual = "manual"
    course = "course"
    resume = "resume"
    completion = "completion"


def _coerce_enum(enum_type: type[StrEnum], value: object, field: str):
    """Accept the enum itself or its exact string value; reject anything else."""
    try:
        return enum_type(value)
    except ValueError:
        allowed = ", ".join(member.value for member in enum_type)
        raise InvalidSkillVectorError(
            f"{field} must be one of: {allowed} (got {value!r})"
        ) from None


def _coerce_confidence(value: object) -> Decimal | None:
    """Normalise to decimal(3,2) in 0.00-1.00. None means a manually declared skill."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        raise InvalidSkillVectorError(f"confidence must be a number or None (got {value!r})")
    number = Decimal(str(value))
    if not number.is_finite() or not Decimal("0") <= number <= Decimal("1"):
        raise InvalidSkillVectorError(f"confidence must be between 0.00 and 1.00 (got {value!r})")
    return number.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class SkillVectorEntry:
    """One row of a student's skill vector (section 1 of docs/CONTRACTS.md).

    Validated on creation. `level` and `source` may be given as the enum or its
    string value; `confidence` is stored as a Decimal rounded to two places.
    """

    canonical_skill_id: int
    canonical_skill_name: str  # display only, never matched on
    level: Level
    confidence: Decimal | None
    source: Source

    def __post_init__(self) -> None:
        if isinstance(self.canonical_skill_id, bool) or not isinstance(
            self.canonical_skill_id, int
        ):
            raise InvalidSkillVectorError("canonical_skill_id must be an integer skill id")
        if not isinstance(self.canonical_skill_name, str) or not self.canonical_skill_name.strip():
            raise InvalidSkillVectorError("canonical_skill_name must be a non-empty string")
        if len(self.canonical_skill_name) > NAME_MAX_LENGTH:
            raise InvalidSkillVectorError(
                f"canonical_skill_name must be at most {NAME_MAX_LENGTH} characters"
            )
        object.__setattr__(self, "level", _coerce_enum(Level, self.level, "level"))
        object.__setattr__(self, "source", _coerce_enum(Source, self.source, "source"))
        object.__setattr__(self, "confidence", _coerce_confidence(self.confidence))


@dataclass(frozen=True)
class SkillVector:
    """A student's skills. Each canonical skill appears at most once.

    Entries are kept sorted by canonical_skill_id so output is deterministic.
    """

    entries: tuple[SkillVectorEntry, ...] = ()

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        seen: set[int] = set()
        for entry in entries:
            if not isinstance(entry, SkillVectorEntry):
                raise InvalidSkillVectorError("a skill vector may only contain SkillVectorEntry")
            if entry.canonical_skill_id in seen:
                raise InvalidSkillVectorError(
                    f"skill {entry.canonical_skill_id} appears more than once in the vector"
                )
            seen.add(entry.canonical_skill_id)
        object.__setattr__(
            self, "entries", tuple(sorted(entries, key=lambda e: e.canonical_skill_id))
        )

    def __iter__(self):
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, skill_id: object) -> bool:
        return any(entry.canonical_skill_id == skill_id for entry in self.entries)

    def get(self, skill_id: int) -> SkillVectorEntry | None:
        for entry in self.entries:
            if entry.canonical_skill_id == skill_id:
                return entry
        return None
