import pytest
from pydantic import ValidationError

from backend.evidence.schemas import EvidenceCreate
from backend.progress.enums import EvidenceType
from backend.progress.exceptions import NotFoundError
from backend.progress.service import ProgressService
from tests.fakes import FakeCatalogue, FakeRecommendations, FakeSkillVector


def test_valid_quiz_evidence_is_linked_to_progress(db):
    svc = ProgressService(db, FakeCatalogue(), FakeSkillVector(), FakeRecommendations())
    progress = svc.enrol("S-01", "LI-1001")
    evidence = svc.add_evidence(
        "S-01",
        progress.progress_id,
        EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=82),
    )
    assert evidence.progress_id == progress.progress_id
    assert progress.score == 82


@pytest.mark.parametrize("score", [-1, 101])
def test_tc_f3_07_rejects_invalid_quiz_score(score):
    with pytest.raises(ValidationError):
        EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=score)


def test_quiz_evidence_requires_score():
    with pytest.raises(ValidationError):
        EvidenceCreate(evidence_type=EvidenceType.QUIZ)


def test_certificate_requires_url_or_metadata():
    with pytest.raises(ValidationError):
        EvidenceCreate(evidence_type=EvidenceType.CERTIFICATE)


def test_evidence_cannot_be_attached_to_other_students_progress(db):
    svc = ProgressService(db, FakeCatalogue(), FakeSkillVector(), FakeRecommendations())
    progress = svc.enrol("S-01", "LI-1001")
    with pytest.raises(NotFoundError):
        svc.add_evidence(
            "S-02",
            progress.progress_id,
            EvidenceCreate(evidence_type=EvidenceType.QUIZ, score=82),
        )
