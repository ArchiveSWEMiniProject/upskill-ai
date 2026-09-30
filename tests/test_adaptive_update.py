from backend.evidence.schemas import EvidenceCreate
from backend.progress.enums import EvidenceType
from backend.progress.exceptions import DependencyUnavailableError
from backend.progress.ports import LearningItem
from backend.progress.service import ProgressService
from tests.fakes import FakeCatalogue, FakeRecommendations, FakeSkillVector


def test_tc_f3_11_recommendation_failure_is_sanitized(db):
    skills = FakeSkillVector(changed=True)
    recs = FakeRecommendations(error=RuntimeError("SYNTHETIC_TEST_FAILURE"))
    svc = ProgressService(db, FakeCatalogue(), skills, recs)
    p = svc.enrol("S-01", "LI-1001")
    svc.add_evidence(
        "S-01", p.progress_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=90)
    )
    try:
        svc.complete("S-01", p.progress_id)
    except DependencyUnavailableError as exc:
        assert "SYNTHETIC_TEST_FAILURE" not in str(exc)
    else:
        raise AssertionError("expected downstream error")
    assert p.status.value == "completed"
    assert p.recommendation_status == "unavailable"


def test_repeated_completion_retries_failed_recommendation_without_duplicate_skill_update(db):
    skills = FakeSkillVector(changed=True)
    p = ProgressService(
        db, FakeCatalogue(), skills, FakeRecommendations(error=RuntimeError("offline"))
    ).enrol("S-01", "LI-1001")
    progress_id = p.progress_id
    ProgressService(
        db, FakeCatalogue(), skills, FakeRecommendations(error=RuntimeError("offline"))
    ).add_evidence("S-01", progress_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=95))
    first = ProgressService(
        db, FakeCatalogue(), skills, FakeRecommendations(error=RuntimeError("offline"))
    )
    try:
        first.complete("S-01", progress_id)
    except DependencyUnavailableError:
        pass
    recs = FakeRecommendations()
    result = ProgressService(db, FakeCatalogue(), skills, recs).complete("S-01", progress_id)
    assert result["recommendation_status"] == "recomputed"
    assert len(skills.calls) == 1
    assert recs.calls == ["S-01"]


def test_tc_f3_09_re_ranking_preserves_other_progress_and_history(db):
    catalogue = FakeCatalogue(
        {
            "LI-1001": FakeCatalogue().items["LI-1001"],
            "LI-1002": LearningItem(
                resource_id="LI-1002",
                title="SQL",
                evidence_required=False,
                evidence_types=(),
                skill_outcomes=(),
            ),
        }
    )
    skills = FakeSkillVector(changed=True)
    recommendations = FakeRecommendations()
    svc = ProgressService(db, catalogue, skills, recommendations)
    first = svc.enrol("S-01", "LI-1001")
    second = svc.enrol("S-01", "LI-1002")
    first_id, second_id = first.progress_id, second.progress_id
    svc.update_progress("S-01", second_id, 40)
    svc.add_evidence("S-01", first_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=90))
    svc.complete("S-01", first_id)
    records = svc.list_enrolments("S-01")
    assert [p.progress_id for p in records] == [first_id, second_id]
    saved_second = next(p for p in records if p.progress_id == second_id)
    assert saved_second.completion_percentage == 40
    assert [event["action"] for event in saved_second.progress_history] == [
        "enrolled",
        "progress-updated",
    ]
    assert recommendations.calls == ["S-01"]
