import pytest

from backend.dashboard.models import Milestone
from backend.evidence.models import CompletionEvidence
from backend.evidence.schemas import EvidenceCreate
from backend.progress.enums import EvidenceType, ProgressStatus
from backend.progress.exceptions import (
    ConflictError,
    DependencyUnavailableError,
    InvalidInputError,
    NotFoundError,
)
from backend.progress.models import Progress
from backend.progress.service import ProgressService
from tests.fakes import FakeCatalogue, FakeRecommendations, FakeSkillVector


def service(db, catalogue=None, skills=None, recommendations=None):
    return ProgressService(
        db,
        catalogue or FakeCatalogue(),
        skills or FakeSkillVector(),
        recommendations or FakeRecommendations(),
    )


def test_tc_f3_01_enrols_with_initial_state(db):
    progress = service(db).enrol("S-01", "LI-1001")
    assert progress.status == ProgressStatus.ENROLLED
    assert progress.completion_percentage == 0


def test_duplicate_enrolment_is_rejected(db):
    svc = service(db)
    svc.enrol("S-01", "LI-1001")
    with pytest.raises(ConflictError):
        svc.enrol("S-01", "LI-1001")


def test_tc_f3_02_invalid_resource_is_rejected_without_record(db):
    svc = service(db)
    with pytest.raises(NotFoundError):
        svc.enrol("S-01", "LI-999999")
    assert svc.list_enrolments("S-01") == []


def test_tc_f3_03_accepts_percentage_and_sets_in_progress(db):
    svc = service(db)
    p = svc.enrol("S-01", "LI-1001")
    updated = svc.update_progress("S-01", p.progress_id, 60)
    assert updated.completion_percentage == 60
    assert updated.status == ProgressStatus.IN_PROGRESS


@pytest.mark.parametrize("percentage", [-1, 101])
def test_tc_f3_04_rejects_out_of_range_percentage(db, percentage):
    svc = service(db)
    p = svc.enrol("S-01", "LI-1001")
    with pytest.raises(InvalidInputError):
        svc.update_progress("S-01", p.progress_id, percentage)
    assert p.completion_percentage == 0


def test_tc_f3_05_blocks_completion_without_enrolment(db):
    with pytest.raises(NotFoundError):
        service(db).complete("S-01", 900)


def test_tc_f3_06_requires_evidence_before_completion(db):
    svc = service(db)
    p = svc.enrol("S-01", "LI-1001")
    with pytest.raises(ConflictError, match="evidence"):
        svc.complete("S-01", p.progress_id)


def test_repeated_completion_is_idempotent(db):
    skills = FakeSkillVector(changed=True)
    recs = FakeRecommendations()
    svc = service(db, skills=skills, recommendations=recs)
    p = svc.enrol("S-01", "LI-1001")
    svc.add_evidence(
        "S-01", p.progress_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=90)
    )
    first = svc.complete("S-01", p.progress_id)
    second = svc.complete("S-01", p.progress_id)
    assert first["already_completed"] is False
    assert second["already_completed"] is True
    assert len(skills.calls) == 1
    assert recs.calls == ["S-01"]
    assert db.query(Progress).filter_by(student_id="S-01").count() == 1
    assert db.query(CompletionEvidence).filter_by(progress_id=p.progress_id).count() == 1
    assert db.query(Milestone).filter_by(progress_id=p.progress_id).count() == 1
    assert [event["action"] for event in first["progress"].progress_history] == [
        "enrolled",
        "completed",
    ]


def test_tc_f3_10_skill_update_uses_completion_source_and_triggers_recompute(db):
    skills = FakeSkillVector(changed=True)
    recs = FakeRecommendations()
    svc = service(db, skills=skills, recommendations=recs)
    p = svc.enrol("S-01", "LI-1001")
    svc.add_evidence(
        "S-01", p.progress_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=90)
    )
    result = svc.complete("S-01", p.progress_id)
    assert skills.calls[0]["source"] == "completion"
    assert recs.calls == ["S-01"]
    assert result["roadmap_version"] == "v2"


def test_equal_or_lower_vector_noop_does_not_recompute(db):
    skills = FakeSkillVector(changed=False)
    recs = FakeRecommendations()
    svc = service(db, skills=skills, recommendations=recs)
    p = svc.enrol("S-01", "LI-1001")
    svc.add_evidence(
        "S-01", p.progress_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=90)
    )
    result = svc.complete("S-01", p.progress_id)
    assert result["skill_vector_changed"] is False
    assert recs.calls == []


def test_skill_adapter_failure_preserves_completion_for_retry(db):
    p = service(db).enrol("S-01", "LI-1001")
    progress_id = p.progress_id
    svc = service(db, skills=FakeSkillVector(error=RuntimeError("private detail")))
    svc.add_evidence(
        "S-01", p.progress_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=90)
    )
    with pytest.raises(DependencyUnavailableError, match="Skill update"):
        svc.complete("S-01", progress_id)
    persisted = db.get(Progress, progress_id)
    assert persisted.status == ProgressStatus.COMPLETED
    assert persisted.skill_update_status == "unavailable"

    skills = FakeSkillVector(changed=True)
    recs = FakeRecommendations()
    retry = service(db, skills=skills, recommendations=recs)
    result = retry.complete("S-01", progress_id)
    assert result["already_completed"] is True
    assert recs.calls == ["S-01"]
