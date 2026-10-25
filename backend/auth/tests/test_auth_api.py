"""API Integration tests for Authentication & Authorization.

Directly verifies:
- TC-F4-01: Valid login issues a token and grants access to protected routes
- TC-F4-02: Invalid password rejected without revealing which field was wrong
- TC-F4-03: Stored passwords are never held in plaintext (Argon2id)
- TC-F4-04: Student cannot access administrator-only endpoint (POST /catalogue)
- TC-F4-05: Faculty mentor cannot perform administrator catalogue management
  (PATCH /catalogue/{id}/moderate)
- TC-F4-06: Faculty mentor cannot view unassigned student
- TC-F4-12: Authorisation enforced server-side
- TC-F4-18: Authorisation error returns 403 Forbidden on breach
"""

from backend.auth.models import UserAccount


def test_tc_f4_01_valid_login_grants_access(client):
    """TC-F4-01: Verify a valid login issues a token and grants access."""
    # Step 1: Submit valid credentials to login endpoint
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "s1@pes.edu", "password": "StudentPass#2026"},
    )
    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "s1@pes.edu"
    assert data["user"]["role"] == "student"

    token = data["access_token"]

    # Step 2: Use returned token on protected route
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "s1@pes.edu"
    assert me_data["role"] == "student"


def test_tc_f4_02_invalid_credentials_rejected_generically(client):
    """TC-F4-02: Verify invalid password rejected without revealing which field was wrong."""
    # Valid email, incorrect password
    resp1 = client.post(
        "/api/v1/auth/login",
        json={"email": "s1@pes.edu", "password": "WrongPassword#999"},
    )
    assert resp1.status_code == 401
    assert "access_token" not in resp1.json()
    assert resp1.json()["detail"] == "Invalid email or password"

    # Non-existent email
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@pes.edu", "password": "AnyPassword#999"},
    )
    assert resp2.status_code == 401
    assert "access_token" not in resp2.json()
    # Same generic message prevents user enumeration
    assert resp2.json()["detail"] == "Invalid email or password"


def test_tc_f4_03_stored_password_is_argon2id(client, db_session):
    """TC-F4-03: Verify stored passwords are never held in plaintext."""
    raw_password = "TestPass#2026"
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newstudent@pes.edu",
            "password": raw_password,
            "role": "student",
            "name": "New Student",
        },
    )
    assert reg_response.status_code == 201

    # Inspect stored user record in DB
    user_record = (
        db_session.query(UserAccount)
        .filter(UserAccount.email == "newstudent@pes.edu")
        .first()
    )
    assert user_record is not None
    assert user_record.password_hash.startswith("$argon2id$")
    assert raw_password not in user_record.password_hash


def test_tc_f4_04_student_blocked_from_admin_catalogue_creation(client, student1_token):
    """TC-F4-04: Verify a student cannot access administrator-only endpoint (REQ-F4-03)."""
    payload = {
        "title": "Intro to Go",
        "description": "Learn Go fundamentals from scratch with hands-on practice.",
        "item_type": "course",
        "level": "beginner",
        "source_url": "https://example.com/go-course",
        "skill_tags": [{"skill_id": 4, "coverage_level": "beginner"}],
    }

    response = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {student1_token}"},
        json=payload,
    )

    # Must be rejected with 403 Forbidden
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_tc_f4_05_faculty_blocked_from_catalogue_moderation(client, admin_token, faculty_token):
    """TC-F4-05: Verify a faculty mentor cannot perform admin catalogue management (REQ-F4-04)."""
    # Create item as admin first
    create_resp = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Docker in Action",
            "description": "Deep dive into container management and deployment.",
            "item_type": "course",
            "level": "intermediate",
            "source_url": "https://example.com/docker",
            "skill_tags": [{"skill_id": 1, "coverage_level": "intermediate"}],
        },
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["item_id"]

    # Faculty attempts to moderate the resource
    mod_resp = client.patch(
        f"/api/v1/catalogue/{item_id}/moderate",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={"moderation_state": "approved"},
    )

    # Must be rejected with 403 Forbidden
    assert mod_resp.status_code == 403
    assert "Access denied" in mod_resp.json()["detail"]


def test_tc_f4_06_faculty_mentee_scoping(client, faculty_token):
    """TC-F4-06: Verify a faculty mentor cannot view unassigned student (REQ-F4-13)."""
    # Student 102 is NOT assigned to Faculty 2 -> must return 403
    resp_unassigned = client.get(
        "/api/v1/faculty/mentees/102",
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert resp_unassigned.status_code == 403
    assert "Access denied" in resp_unassigned.json()["detail"]

    # Student 101 IS assigned to Faculty 2 -> returns 200
    resp_assigned = client.get(
        "/api/v1/faculty/mentees/101",
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert resp_assigned.status_code == 200
    assert resp_assigned.json()["student_id"] == 101


def test_tc_f4_12_server_side_enforcement(client, student1_token):
    """TC-F4-12: Direct API call without frontend bypass is strictly blocked server-side."""
    resp = client.patch(
        "/api/v1/catalogue/1/moderate",
        headers={"Authorization": f"Bearer {student1_token}"},
        json={"moderation_state": "approved"},
    )
    assert resp.status_code == 403
