"""Tests for the auth FastAPI dependencies (CA-1, CA-2), backfilled in Sprint 3.

get_current_user, require_role and require_permission are called directly so
every rejection path is checked without needing a route for each one.
Fixture users (conftest.py): 1 administrator, 2 faculty mentor, 3 and 4 students.
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from backend.auth.dependencies import get_current_user, require_permission, require_role
from backend.auth.models import UserAccount, UserContext, UserRole
from backend.auth.security import create_access_token

ADMIN = UserContext(user_id=1, email="admin@pes.edu", role=UserRole.ADMINISTRATOR)
STUDENT = UserContext(user_id=3, email="s1@pes.edu", role=UserRole.STUDENT)


def assert_status(excinfo, code: int) -> None:
    assert excinfo.value.status_code == code


# --- get_current_user -----------------------------------------------------------


def test_valid_token_returns_user_context_from_the_database(db_session):
    token = create_access_token({"sub": "3", "role": "student"})
    user = get_current_user(token=token, db=db_session)
    assert user == UserContext(
        user_id=3, email="s1@pes.edu", role=UserRole.STUDENT, is_active=True
    )


def test_user_id_claim_is_accepted_when_sub_is_missing(db_session):
    token = create_access_token({"user_id": 2, "role": "faculty_mentor"})
    assert get_current_user(token=token, db=db_session).role is UserRole.FACULTY_MENTOR


def test_role_comes_from_the_database_not_the_token(db_session):
    """A student who edits their token's role claim still gets the student role."""
    token = create_access_token({"sub": "3", "role": "administrator"})
    assert get_current_user(token=token, db=db_session).role is UserRole.STUDENT


# Tokens are built inside the test: JWT_SECRET is only set once fixtures run.
@pytest.mark.parametrize(
    "make_token",
    [
        lambda: None,
        lambda: "",
        lambda: "not-a-jwt",
        lambda: create_access_token({"role": "student"}),
        lambda: create_access_token({"sub": "3"}),
        lambda: create_access_token({"sub": "abc", "role": "student"}),
        lambda: create_access_token({"sub": "3", "role": "superuser"}),
        lambda: create_access_token({"sub": "3", "role": "student"}, timedelta(seconds=-1)),
        lambda: create_access_token({"sub": "999", "role": "student"}),
    ],
    ids=[
        "missing", "empty", "malformed", "no-sub", "no-role", "sub-not-an-int",
        "unknown-role", "expired", "unknown-user",
    ],
)
def test_invalid_tokens_get_a_generic_401(db_session, make_token):
    token = make_token()
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(token=token, db=db_session)
    assert_status(excinfo, 401)
    assert excinfo.value.detail == "Could not validate credentials"
    assert excinfo.value.headers == {"WWW-Authenticate": "Bearer"}


def test_deactivated_account_is_rejected(db_session):
    db_session.query(UserAccount).filter(UserAccount.user_id == 4).update({"is_active": False})
    db_session.flush()
    token = create_access_token({"sub": "4", "role": "student"})
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(token=token, db=db_session)
    assert_status(excinfo, 401)


# --- require_role ---------------------------------------------------------------


def test_require_role_passes_an_allowed_role_through():
    checker = require_role(UserRole.ADMINISTRATOR, UserRole.FACULTY_MENTOR)
    assert checker(user=ADMIN) is ADMIN


def test_require_role_rejects_other_roles_with_403():
    checker = require_role(UserRole.ADMINISTRATOR)
    with pytest.raises(HTTPException) as excinfo:
        checker(user=STUDENT)
    assert_status(excinfo, 403)
    assert excinfo.value.detail == "Access denied: role not permitted"


# --- require_permission ---------------------------------------------------------


def test_require_permission_allows_when_authorize_does(db_session):
    checker = require_permission("catalogue:create")
    assert checker(user=ADMIN, db=db_session) is ADMIN


def test_require_permission_rejects_with_403_naming_the_action(db_session):
    checker = require_permission("catalogue:create")
    with pytest.raises(HTTPException) as excinfo:
        checker(user=STUDENT, db=db_session)
    assert_status(excinfo, 403)
    assert excinfo.value.detail == "Access denied: unauthorized for action 'catalogue:create'"


def test_require_permission_passes_the_provided_resource_to_authorize(db_session):
    own = require_permission("profile:read", resource_provider=lambda: {"user_id": 3})
    other = require_permission("profile:read", resource_provider=lambda: {"user_id": 4})
    assert own(user=STUDENT, db=db_session) is STUDENT
    with pytest.raises(HTTPException) as excinfo:
        other(user=STUDENT, db=db_session)
    assert_status(excinfo, 403)
