from backend.dashboard.service import DashboardService
from backend.evidence.schemas import EvidenceCreate
from backend.progress.enums import EvidenceType
from backend.progress.service import ProgressService
from tests.fakes import FakeCatalogue, FakeRecommendations, FakeSkillVector


def test_dashboard_reports_enrolment_progress_completion_and_milestone(db):
    svc = ProgressService(
        db, FakeCatalogue(), FakeSkillVector(changed=False), FakeRecommendations()
    )
    p = svc.enrol("S-01", "LI-1001")
    svc.update_progress("S-01", p.progress_id, 60)
    svc.add_evidence(
        "S-01", p.progress_id, EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=90)
    )
    svc.complete("S-01", p.progress_id)
    result = DashboardService(db).get("S-01")
    assert result.completed_count == 1
    assert result.active_count == 0
    assert result.enrolments[0].completion_percentage == 100
    assert result.enrolments[0].evidence_status == "verified"
    assert result.milestones[0]["kind"] == "completed"
    assert result.gaps_status == "pending-m2-integration"


def test_dashboard_is_scoped_to_student(db):
    svc = ProgressService(db, FakeCatalogue(), FakeSkillVector(), FakeRecommendations())
    svc.enrol("S-01", "LI-1001")
    result = DashboardService(db).get("S-02")
    assert result.enrolments == []
    assert result.progress_percent == 0
