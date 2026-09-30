from fastapi.testclient import TestClient

from backend.app import app
from backend.config import settings
from backend.database import get_db
from backend.progress.dependencies import get_service
from backend.progress.service import ProgressService
from tests.fakes import FakeCatalogue, FakeRecommendations, FakeSkillVector


def test_api_student_scope_and_auth_placeholder(db):
    service = ProgressService(db, FakeCatalogue(), FakeSkillVector(), FakeRecommendations())
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)
    try:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/v1/progress/enrolments").status_code == 401
        created = client.post(
            "/api/v1/progress/enrolments",
            headers={"X-Student-Id": "S-01"},
            json={"resource_id": "LI-1001"},
        )
        assert created.status_code == 201
        progress_id = created.json()["progress_id"]
        other_student = client.get("/api/v1/progress/enrolments", headers={"X-Student-Id": "S-02"})
        assert other_student.json() == []
        denied = client.get(
            f"/api/v1/progress/enrolments/{progress_id}/evidence",
            headers={"X-Student-Id": "S-02"},
        )
        assert denied.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_certificate_upload_and_owner_scoped_download(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "evidence_storage_dir", str(tmp_path))
    service = ProgressService(db, FakeCatalogue(), FakeSkillVector(), FakeRecommendations())
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)
    try:
        created = client.post(
            "/api/v1/progress/enrolments",
            headers={"X-Student-Id": "S-01"},
            json={"resource_id": "LI-1001"},
        )
        progress_id = created.json()["progress_id"]
        uploaded = client.post(
            f"/api/v1/progress/enrolments/{progress_id}/evidence/file",
            headers={"X-Student-Id": "S-01"},
            files={"file": ("certificate.pdf", b"%PDF-1.7 test", "application/pdf")},
        )
        assert uploaded.status_code == 201
        file_key = uploaded.json()["evidence_url"].rsplit("/", 1)[-1]
        downloaded = client.get(
            f"/api/v1/progress/evidence-files/{file_key}",
            headers={"X-Student-Id": "S-01"},
        )
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF-")
        denied = client.get(
            f"/api/v1/progress/evidence-files/{file_key}",
            headers={"X-Student-Id": "S-02"},
        )
        assert denied.status_code == 404
    finally:
        app.dependency_overrides.clear()
