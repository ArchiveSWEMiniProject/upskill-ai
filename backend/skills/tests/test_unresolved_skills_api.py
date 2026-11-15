"""UP-10: skill strings that do not resolve are kept and the student is asked
to map them (TC-F1-09, REQ-F1-22), against real Postgres."""

from sqlalchemy import select

from backend.skills.models import StudentSkill, UnresolvedSkill

SKILLS = "/api/v1/profile/skills"
UNRESOLVED = f"{SKILLS}/unresolved"


def declare_unknown(client, headers, text="Quantum Blockchain Fabric"):
    return client.post(SKILLS, json={"skill": text, "level": "beginner"}, headers=headers)


def open_rows(db_session):
    return list(db_session.scalars(select(UnresolvedSkill).order_by(UnresolvedSkill.unresolved_id)))


def test_an_unknown_skill_is_recorded_and_the_student_gets_its_id(
    client, db_session, skill_ids, student
):
    response = declare_unknown(client, student, "  Pythn ")

    assert response.status_code == 422
    detail = response.json()["detail"]
    rows = open_rows(db_session)
    assert len(rows) == 1
    assert detail["unresolved_id"] == rows[0].unresolved_id
    assert (rows[0].raw_text, rows[0].normalised_text, rows[0].status) == (
        "Pythn", "pythn", "open",
    )
    assert rows[0].mapped_skill_id is None


def test_asking_again_for_the_same_unknown_text_does_not_duplicate(
    client, db_session, skill_ids, student
):
    first = declare_unknown(client, student, "Pythn").json()["detail"]["unresolved_id"]
    second = declare_unknown(client, student, "PYTHN ").json()["detail"]["unresolved_id"]

    assert first == second
    assert len(open_rows(db_session)) == 1


def test_a_resolvable_skill_records_nothing(client, db_session, skill_ids, student):
    client.post(SKILLS, json={"skill": "python", "level": "beginner"}, headers=student)
    assert open_rows(db_session) == []


def test_the_student_is_shown_open_strings_with_suggestions(client, skill_ids, student):
    declare_unknown(client, student, "Pythn")

    listed = client.get(UNRESOLVED, headers=student).json()

    assert len(listed) == 1
    assert listed[0]["raw_text"] == "Pythn"
    assert listed[0]["suggestions"][0] == {
        "skill_id": skill_ids["Python"], "skill_name": "Python",
    }


def test_mapping_declares_the_skill_and_closes_the_string(
    client, db_session, skill_ids, student
):
    unresolved_id = declare_unknown(client, student, "Pythn").json()["detail"]["unresolved_id"]

    response = client.post(
        f"{UNRESOLVED}/{unresolved_id}/map",
        json={"skill_id": skill_ids["Python"], "level": "intermediate"},
        headers=student,
    )

    assert response.status_code == 200, response.json()
    assert response.json()["skill_name"] == "Python"
    skills = db_session.scalars(select(StudentSkill)).all()
    assert [(s.skill_id, s.level, s.source) for s in skills] == [
        (skill_ids["Python"], "intermediate", "manual")
    ]
    row = open_rows(db_session)[0]
    assert (row.status, row.mapped_skill_id) == ("mapped", skill_ids["Python"])
    assert client.get(UNRESOLVED, headers=student).json() == []


def test_a_mapped_string_cannot_be_mapped_twice(client, skill_ids, student):
    unresolved_id = declare_unknown(client, student, "Pythn").json()["detail"]["unresolved_id"]
    body = {"skill_id": skill_ids["Python"], "level": "beginner"}
    client.post(f"{UNRESOLVED}/{unresolved_id}/map", json=body, headers=student)

    again = client.post(f"{UNRESOLVED}/{unresolved_id}/map", json=body, headers=student)

    assert again.status_code == 404


def test_mapping_to_a_skill_outside_the_taxonomy_is_rejected(
    client, db_session, skill_ids, student
):
    unresolved_id = declare_unknown(client, student, "Pythn").json()["detail"]["unresolved_id"]

    response = client.post(
        f"{UNRESOLVED}/{unresolved_id}/map",
        json={"skill_id": 999_999, "level": "beginner"},
        headers=student,
    )

    assert response.status_code == 422
    assert open_rows(db_session)[0].status == "open"
    assert db_session.scalars(select(StudentSkill)).all() == []


def test_a_student_cannot_see_or_map_another_students_strings(
    client, skill_ids, student, make_user, bearer
):
    unresolved_id = declare_unknown(client, student, "Pythn").json()["detail"]["unresolved_id"]
    other = bearer(make_user())
    client.post("/api/v1/profile", json={"name": "Ben"}, headers=other)

    assert client.get(UNRESOLVED, headers=other).json() == []
    response = client.post(
        f"{UNRESOLVED}/{unresolved_id}/map",
        json={"skill_id": skill_ids["Python"], "level": "beginner"},
        headers=other,
    )
    assert response.status_code == 404


def test_without_a_profile_it_is_a_404(client, skill_ids, make_user, bearer):
    headers = bearer(make_user())
    assert client.get(UNRESOLVED, headers=headers).status_code == 404
    assert client.get(UNRESOLVED).status_code == 401
