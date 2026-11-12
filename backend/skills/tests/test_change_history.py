"""UP-14 (reduced): every real change to a student's skills writes one
skill_change_history row (REQ-F1-06, F1-07; asserted for TC-F1-14), against
real Postgres. There is no student-facing history view (scope cut, plan.md §2).

A row holds the skill, the previous level (None when the skill is new), the
new level, the source and a timestamp. A call that changes nothing writes
nothing. The resume path (UP-8) writes its rows the same way and is covered in
its own tests.
"""

from datetime import datetime

import pytest
from sqlalchemy import select

from backend.skills.models import SkillChangeHistory
from backend.skills.vector import apply_vector_update

SKILLS = "/api/v1/profile/skills"


@pytest.fixture
def student_id(client, student) -> int:
    return client.get("/api/v1/profile", headers=student).json()["student_id"]


def declare(client, headers, skill, level):
    response = client.post(SKILLS, json={"skill": skill, "level": level}, headers=headers)
    assert response.status_code in (200, 201), response.json()


def rows(db_session, student_id) -> list[SkillChangeHistory]:
    return list(
        db_session.scalars(
            select(SkillChangeHistory)
            .where(SkillChangeHistory.student_id == student_id)
            .order_by(SkillChangeHistory.history_id)
        )
    )


def summary(db_session, student_id) -> list[tuple]:
    return [
        (r.skill_id, r.previous_level, r.new_level, r.source)
        for r in rows(db_session, student_id)
    ]


def test_every_real_change_writes_one_row_with_its_previous_level(
    client, db_session, skill_ids, student, student_id
):
    python = skill_ids["Python"]

    declare(client, student, "python", "beginner")  # new skill
    declare(client, student, "py", "beginner")  # same level, another spelling: no change
    declare(client, student, "Python", "intermediate")  # manual change
    apply_vector_update(student_id, python, "intermediate", "completion", session=db_session)
    apply_vector_update(student_id, python, "advanced", "completion", session=db_session)
    apply_vector_update(student_id, python, "beginner", "completion", session=db_session)

    # The two completion calls that are not higher than the held level write
    # nothing. previous_level is the level held from that row's own source,
    # so the first completion raise starts from None.
    assert summary(db_session, student_id) == [
        (python, None, "beginner", "manual"),
        (python, "beginner", "intermediate", "manual"),
        (python, None, "advanced", "completion"),
    ]


def test_every_row_is_timestamped_in_order(client, db_session, skill_ids, student, student_id):
    declare(client, student, "python", "beginner")
    declare(client, student, "sql", "beginner")
    react = skill_ids["React"]
    apply_vector_update(student_id, react, "beginner", "completion", session=db_session)

    history = rows(db_session, student_id)
    assert len(history) == 3
    stamps = [r.changed_at for r in history]
    assert all(isinstance(s, datetime) and s.tzinfo is not None for s in stamps)
    assert stamps == sorted(stamps)


def test_history_is_kept_per_student(client, db_session, skill_ids, student, student_id,
                                     make_user, bearer):
    other = bearer(make_user())
    assert client.post("/api/v1/profile", json={"name": "Ravi"}, headers=other).status_code == 201
    other_id = client.get("/api/v1/profile", headers=other).json()["student_id"]

    declare(client, student, "python", "beginner")
    declare(client, other, "sql", "intermediate")

    assert summary(db_session, student_id) == [(skill_ids["Python"], None, "beginner", "manual")]
    assert summary(db_session, other_id) == [
        (skill_ids["SQL Basics"], None, "intermediate", "manual")
    ]


def test_a_rejected_change_writes_no_row(client, db_session, skill_ids, student, student_id):
    response = client.post(
        SKILLS, json={"skill": "not-a-real-skill", "level": "beginner"}, headers=student
    )
    assert response.status_code == 422
    assert rows(db_session, student_id) == []
