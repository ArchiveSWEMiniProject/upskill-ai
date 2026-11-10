"""Dashboard history and metrics through the authenticated M3 read route."""

from datetime import UTC, date, datetime
from unittest.mock import Mock

from backend.dashboard.schemas import GapSummary
from backend.dashboard.service import _current_streak, get_gap_summary_reader
from backend.main import app
from backend.progress.models import ProgressEvent


def test_dashboard_scopes_history_and_reads_gap_summary(
    client, student, resource, bearer, make_user, db_session,
):
    headers = bearer(student[0])
    enrol = "/api/v1/progress/enrol"
    path = "/api/v1/progress/dashboard"
    resource_id = resource()
    other_resource = resource()
    first = client.post(enrol, json={"resource_id": resource_id}, headers=headers).json()
    progress_url = f'/api/v1/progress/{first["progress_id"]}'
    assert client.patch(progress_url, json={"completion_percentage": 60},
                        headers=headers).status_code == 200
    assert client.post(f"{progress_url}/complete", json={}, headers=headers).status_code == 200
    other_headers = bearer(make_user())
    assert client.post("/api/v1/profile", json={"name": "Other"},
                       headers=other_headers).status_code == 201
    assert client.post(enrol, json={"resource_id": other_resource},
                       headers=other_headers).status_code == 201

    assert client.get(path).status_code == 401
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["gap_summary"] is None and result["gap_closure_proportion"] is None
    assert result["completed_count"] == 1
    assert result["current_streak_days"] == 1
    assert result["milestones"][0]["label"] == "First resource completed"
    assert [row["resource_id"] for row in result["resources"]] == [resource_id]
    item = result["resources"][0]
    assert item["title"] == "Learning resource"
    assert [row["completion_percentage"] for row in item["history"]] == [0, 60, 100]

    reader = Mock(return_value=GapSummary(closed=2, total=4))
    app.dependency_overrides[get_gap_summary_reader] = lambda: reader
    result = client.get(path, headers=headers).json()
    reader.assert_called_once_with(student[1], db_session)
    assert result["gap_summary"] == {"closed": 2, "total": 4}
    assert result["gap_closure_proportion"] == 0.5


def test_streak_counts_distinct_days_with_increases_and_expires_after_a_gap():
    events = [
        ProgressEvent(progress_id=1, status=status, completion_percentage=percent,
                      occurred_at=datetime(2026, 11, day, hour, tzinfo=UTC))
        for day, hour, status, percent in [
            (7, 12, "enrolled", 0), (8, 12, "in-progress", 60),
            (8, 18, "in-progress", 70), (9, 8, "in-progress", 65),
            (9, 10, "completed", 100),
        ]
    ]
    assert _current_streak(events, date(2026, 11, 9)) == 2
    assert _current_streak(events, date(2026, 11, 10)) == 2
    assert _current_streak(events, date(2026, 11, 11)) == 0
