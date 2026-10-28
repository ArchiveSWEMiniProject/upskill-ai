"""UP-5 and UP-9 through the API, against real Postgres."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.profile.models import Student
from backend.skills.models import SkillChangeHistory, StudentSkill
from backend.skills.repository import StudentSkillRepository

URL = "/api/v1/profile/skills"


def manual_rows(db_session) -> list[tuple[int, str]]:
    return list(
        db_session.execute(
            select(StudentSkill.skill_id, StudentSkill.level).where(StudentSkill.source == "manual")
        )
    )


def history(db_session) -> list[tuple]:
    return list(
        db_session.execute(
            select(
                SkillChangeHistory.skill_id,
                SkillChangeHistory.previous_level,
                SkillChangeHistory.new_level,
                SkillChangeHistory.source,
            ).order_by(SkillChangeHistory.history_id)
        )
    )


def test_declares_a_canonical_skill(client, db_session, skill_ids, student):
    response = client.post(URL, json={"skill": "Python", "level": "intermediate"}, headers=student)

    assert response.status_code == 201
    assert response.json() == {
        "skill_id": skill_ids["Python"],
        "skill_name": "Python",
        "level": "intermediate",
        "source": "manual",
    }
    assert manual_rows(db_session) == [(skill_ids["Python"], "intermediate")]
    assert history(db_session) == [(skill_ids["Python"], None, "intermediate", "manual")]


# TC-F1-08, through the real entry path
def test_variant_spellings_resolve_to_one_entry(client, db_session, skill_ids, student):
    statuses = [
        client.post(URL, json={"skill": variant, "level": "beginner"}, headers=student)
        for variant in ["ReactJS", "React.js", "react", " REACT "]
    ]

    assert [r.status_code for r in statuses] == [201, 200, 200, 200]
    assert {r.json()["skill_name"] for r in statuses} == {"React"}
    assert manual_rows(db_session) == [(skill_ids["React"], "beginner")]
    assert len(history(db_session)) == 1  # repeats at the same level change nothing


def test_redeclaring_at_a_new_level_updates_and_records_the_change(
    client, db_session, skill_ids, student
):
    client.post(URL, json={"skill": "py", "level": "beginner"}, headers=student)
    response = client.post(URL, json={"skill": "Python", "level": "advanced"}, headers=student)

    assert response.status_code == 200
    assert response.json()["level"] == "advanced"
    assert manual_rows(db_session) == [(skill_ids["Python"], "advanced")]
    assert history(db_session) == [
        (skill_ids["Python"], None, "beginner", "manual"),
        (skill_ids["Python"], "beginner", "advanced", "manual"),
    ]


# REQ-F1-05
def test_unknown_skill_is_rejected_with_closest_suggestions(
    client, db_session, skill_ids, student
):
    response = client.post(URL, json={"skill": "Pythn", "level": "beginner"}, headers=student)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "Unknown skill: Pythn"
    assert detail["suggestions"][0] == {"skill_id": skill_ids["Python"], "skill_name": "Python"}
    assert manual_rows(db_session) == []


def test_unrelated_unknown_skill_has_no_suggestions(client, skill_ids, student):
    response = client.post(
        URL, json={"skill": "Quantum Blockchain Fabric", "level": "beginner"}, headers=student
    )
    assert response.status_code == 422
    assert response.json()["detail"]["suggestions"] == []


def test_skills_are_kept_per_student(
    client, db_session, skill_ids, make_user, bearer, student
):
    other = bearer(make_user())
    client.post("/api/v1/profile", json={"name": "Ravi"}, headers=other)

    client.post(URL, json={"skill": "sql", "level": "beginner"}, headers=student)
    client.post(URL, json={"skill": "sql", "level": "advanced"}, headers=other)

    levels = sorted(level for _, level in manual_rows(db_session))
    assert levels == ["advanced", "beginner"]


def test_declaring_without_a_profile_returns_404(client, make_user, bearer, skill_ids):
    headers = bearer(make_user())
    response = client.post(URL, json={"skill": "Python", "level": "beginner"}, headers=headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"level": "beginner"}, "skill"),
        ({"skill": "   ", "level": "beginner"}, "skill"),
        ({"skill": "x" * 121, "level": "beginner"}, "skill"),
        ({"skill": "Python"}, "level"),
        ({"skill": "Python", "level": "expert"}, "level"),
        ({"skill": "Python", "level": "Beginner"}, "level"),
        ({"skill": "Python", "level": "beginner", "source": "resume"}, "source"),
    ],
)
def test_invalid_requests_are_rejected_naming_the_field(
    client, db_session, skill_ids, student, payload, field
):
    response = client.post(URL, json=payload, headers=student)
    assert response.status_code == 422
    assert [error["loc"][-1] for error in response.json()["detail"]] == [field]
    assert db_session.scalar(select(func.count()).select_from(StudentSkill)) == 0


def test_requires_authentication(client):
    response = client.post(URL, json={"skill": "Python", "level": "beginner"})
    assert response.status_code == 401



# --- Repository guards ------------------------------------------------------


@pytest.fixture
def student_id(db_session, student) -> int:
    return db_session.scalar(select(func.max(Student.student_id)))


def entry(student_id: int, skill_id: int, level: str) -> StudentSkill:
    return StudentSkill(student_id=student_id, skill_id=skill_id, source="manual", level=level)


def test_duplicate_insert_returns_false_and_keeps_the_transaction_usable(
    db_session, skill_ids, student_id
):
    """Two concurrent first declarations: the primary key stops the second
    insert, and the caller can carry on in the same transaction."""
    repo = StudentSkillRepository(db_session)
    first = entry(student_id, skill_ids["SQL Basics"], "beginner")
    assert repo.add(first) is True
    db_session.expunge(first)  # the winner belongs to another request in a real race

    assert repo.add(entry(student_id, skill_ids["SQL Basics"], "advanced")) is False
    assert manual_rows(db_session) == [(skill_ids["SQL Basics"], "beginner")]


def test_other_integrity_errors_are_raised(db_session, student_id):
    with pytest.raises(IntegrityError):  # skill 999999 does not exist
        StudentSkillRepository(db_session).add(entry(student_id, 999_999, "beginner"))
