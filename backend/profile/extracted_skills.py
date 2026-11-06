"""Extracted resume skills: storing the proposals (UP-7) and the student's
decision on each one (UP-8, REQ-F1-13 and F1-15 to F1-17).

Candidates are written when a resume is read. Nothing reaches student_skill,
and so nothing reaches the skill vector, until the student confirms it
(REQ-F1-15). Each candidate can be confirmed (at the suggested level or an
edited one) or rejected (REQ-F1-16), and every pending candidate at or above
the high-confidence threshold can be confirmed in one action (REQ-F1-17).
The threshold is configuration (RESUME_HIGH_CONFIDENCE_THRESHOLD), not code.

A confirmed skill is stored with source "resume" and the candidate's
confidence; a change to the student's resume-sourced level is written to the
skill change history, like any other skill change (REQ-F1-07).
"""

import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from backend.profile.models import ExtractedSkillCandidate, ResumeUpload
from backend.profile.skill_extraction import Candidate
from backend.profile.staleness import mark_stale
from backend.skills.models import StudentSkill
from backend.skills.repository import StudentSkillRepository

RESUME = "resume"
DEFAULT_THRESHOLD = Decimal("0.80")

_skill = table("skill", column("skill_id"), column("skill_name"))


def high_confidence_threshold() -> Decimal:
    """RESUME_HIGH_CONFIDENCE_THRESHOLD (0 to 1), or 0.80 when unset or invalid."""
    raw = os.environ.get("RESUME_HIGH_CONFIDENCE_THRESHOLD", "")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return DEFAULT_THRESHOLD
    return value if Decimal(0) <= value <= Decimal(1) else DEFAULT_THRESHOLD


class CandidateNotFoundError(Exception):
    """No such candidate on the caller's profile (it may belong to someone else)."""

    message = "Extracted skill not found"


class CandidateAlreadyDecidedError(Exception):
    message = "This extracted skill has already been confirmed or rejected"

    def __init__(self, candidate_id: int):
        super().__init__(self.message)
        self.candidate_id = candidate_id


@dataclass(frozen=True)
class CandidateView:
    candidate_id: int
    upload_id: int
    skill_id: int
    skill_name: str
    suggested_level: str
    confidence: Decimal
    source_sentence: str
    status: str


@dataclass(frozen=True)
class Decision:
    candidate_id: int
    action: str  # confirm | reject
    level: str | None = None  # confirm only; None keeps the suggested level


@dataclass(frozen=True)
class Outcome:
    candidate_id: int
    skill_id: int
    skill_name: str
    status: str  # confirmed | rejected
    level: str | None  # the stored level, for a confirmed skill


class ExtractedSkillService:
    def __init__(self, session: Session, now=lambda: datetime.now(UTC)):
        self._session = session
        self._skills = StudentSkillRepository(session)
        self._now = now

    # --- UP-7: store the proposals --------------------------------------------

    def record(self, upload_id: int, candidates: Iterable[Candidate]) -> int:
        """Store one pending row per candidate for this upload; returns how many."""
        rows = [
            ExtractedSkillCandidate(
                upload_id=upload_id,
                skill_id=c.skill_id,
                suggested_level=c.level,
                confidence=c.confidence,
                source_sentence=c.source_sentence,
                status="pending",
            )
            for c in candidates
        ]
        self._session.add_all(rows)
        self._session.flush()
        return len(rows)

    # --- UP-8: review ---------------------------------------------------------

    def _query(self, student_id: int):
        return (
            select(ExtractedSkillCandidate, _skill.c.skill_name)
            .join(ResumeUpload, ResumeUpload.upload_id == ExtractedSkillCandidate.upload_id)
            .join(_skill, _skill.c.skill_id == ExtractedSkillCandidate.skill_id)
            .where(ResumeUpload.student_id == student_id)
        )

    def candidates(
        self,
        student_id: int,
        *,
        status: str | None = "pending",
        min_confidence: Decimal | None = None,
        upload_id: int | None = None,
    ) -> list[CandidateView]:
        """The caller's candidates, highest confidence first (REQ-F1-13)."""
        query = self._query(student_id)
        if status is not None:
            query = query.where(ExtractedSkillCandidate.status == status)
        if min_confidence is not None:
            query = query.where(ExtractedSkillCandidate.confidence >= min_confidence)
        if upload_id is not None:
            query = query.where(ExtractedSkillCandidate.upload_id == upload_id)
        query = query.order_by(
            ExtractedSkillCandidate.confidence.desc(), ExtractedSkillCandidate.candidate_id
        )
        return [_view(row, name) for row, name in self._session.execute(query)]

    def decide(self, student_id: int, decisions: list[Decision]) -> list[Outcome]:
        """Apply every decision, or none: each candidate is checked first."""
        ids = [d.candidate_id for d in decisions]
        found = {
            row.candidate_id: (row, name)
            for row, name in self._session.execute(
                self._query(student_id)
                .where(ExtractedSkillCandidate.candidate_id.in_(ids))
                # Two requests deciding the same skill: the second waits, then
                # sees it is no longer pending.
                .with_for_update(of=ExtractedSkillCandidate)
            )
        }
        for decision in decisions:
            if decision.candidate_id not in found:
                raise CandidateNotFoundError
            if found[decision.candidate_id][0].status != "pending":
                raise CandidateAlreadyDecidedError(decision.candidate_id)
        outcomes = [self._apply(student_id, *found[d.candidate_id], d) for d in decisions]
        if any(outcome.status == "confirmed" for outcome in outcomes):
            mark_stale(student_id)  # the skill vector changed
        return outcomes

    def confirm_high_confidence(self, student_id: int) -> tuple[Decimal, list[Outcome]]:
        """Confirm, at their suggested levels, all pending candidates at or above
        the threshold (REQ-F1-17). Lower ones stay pending."""
        threshold = high_confidence_threshold()
        pending = self.candidates(student_id, min_confidence=threshold)
        decisions = [Decision(c.candidate_id, "confirm") for c in pending]
        return threshold, self.decide(student_id, decisions)

    def _apply(
        self, student_id: int, row: ExtractedSkillCandidate, name: str, decision: Decision
    ) -> Outcome:
        row.decided_at = self._now()
        if decision.action == "reject":
            row.status = "rejected"
            return Outcome(row.candidate_id, row.skill_id, name, "rejected", None)

        level = decision.level or row.suggested_level
        row.status = "confirmed"
        existing = self._skills.get(student_id, row.skill_id, RESUME)
        if existing is None:
            entry = StudentSkill(
                student_id=student_id,
                skill_id=row.skill_id,
                source=RESUME,
                level=level,
                confidence=row.confidence,
            )
            if self._skills.add(entry):
                self._skills.record_change(student_id, row.skill_id, None, level, RESUME)
                return Outcome(row.candidate_id, row.skill_id, name, "confirmed", level)
            existing = self._skills.get(student_id, row.skill_id, RESUME)
        previous = existing.level
        existing.level = level
        existing.confidence = row.confidence
        if previous != level:
            self._skills.record_change(student_id, row.skill_id, previous, level, RESUME)
        self._session.flush()
        return Outcome(row.candidate_id, row.skill_id, name, "confirmed", level)


def _view(row: ExtractedSkillCandidate, name: str) -> CandidateView:
    return CandidateView(
        candidate_id=row.candidate_id,
        upload_id=row.upload_id,
        skill_id=row.skill_id,
        skill_name=name,
        suggested_level=row.suggested_level,
        confidence=row.confidence,
        source_sentence=row.source_sentence,
        status=row.status,
    )
