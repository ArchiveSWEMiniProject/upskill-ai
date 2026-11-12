"""Branch coverage for authorize() (CA-1), backfilled in Sprint 3.

test_rbac.py covers the main allow/deny cases. These tests pin down the rest:
the different shapes a user or a resource can take, mentee checks with and
without a database, and the actions each role is not given at all.

Fixture data (conftest.py): faculty user 2 mentors student 101 (user 3);
student 102 belongs to user 4.
"""

from types import SimpleNamespace

import pytest

from backend.auth.models import UserContext, UserRole
from backend.auth.permissions import _extract_user_attrs, authorize, require_permission

FACULTY = UserContext(user_id=2, email="faculty@pes.edu", role=UserRole.FACULTY_MENTOR)
STUDENT = UserContext(user_id=3, email="s1@pes.edu", role=UserRole.STUDENT)


# --- user shapes ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        (None, (None, None)),
        ({"user_id": 7, "role": UserRole.STUDENT}, (7, "student")),
        ({"user_id": 7, "role": "ADMINISTRATOR"}, (7, "administrator")),
        ({"user_id": 7}, (7, None)),
        (SimpleNamespace(user_id=8, role=UserRole.FACULTY_MENTOR), (8, "faculty_mentor")),
        (SimpleNamespace(user_id=8, role="Student"), (8, "student")),
        (SimpleNamespace(user_id=8), (8, None)),
        (object(), (None, None)),
    ],
)
def test_extract_user_attrs_accepts_every_supported_shape(user, expected):
    assert _extract_user_attrs(user) == expected


@pytest.mark.parametrize(
    "user",
    [None, {"user_id": 3}, {"role": "student"}, {"user_id": 0, "role": "student"}],
)
def test_missing_user_id_or_role_is_denied(user):
    assert authorize(user, "profile:read") is False


def test_unknown_role_is_denied():
    assert authorize({"user_id": 9, "role": "guest"}, "catalogue:read") is False


def test_dict_and_object_users_are_treated_like_user_context():
    assert authorize({"user_id": 1, "role": "administrator"}, "user:manage") is True
    assert authorize(SimpleNamespace(user_id=3, role="student"), "catalogue:create") is False


def test_action_is_case_insensitive():
    assert authorize(STUDENT, "CATALOGUE:CREATE") is False
    assert authorize(FACULTY, "Catalogue:Read") is True


# --- faculty --------------------------------------------------------------------


@pytest.mark.parametrize("action", ["catalogue:read", "catalogue:search", "resource:read"])
def test_faculty_reads_only_approved_catalogue_resources(action):
    assert authorize(FACULTY, action) is True
    assert authorize(FACULTY, action, resource={"moderation_state": "approved"}) is True
    assert authorize(FACULTY, action, resource={"moderation_state": "pending"}) is False
    assert authorize(FACULTY, action, resource={"title": "no state given"}) is True


def test_faculty_mentee_capability_check_without_a_resource():
    assert authorize(FACULTY, "mentee:view") is True


def test_faculty_mentee_check_from_assigned_ids_in_context():
    assigned = {101, 55}
    assert authorize(FACULTY, "mentee:view", resource=101, assigned_student_ids=assigned) is True
    assert authorize(
        FACULTY, "mentee:view", resource={"user_id": 55}, assigned_student_ids=assigned
    ) is True
    # Not in the set and no database to fall back on.
    assert authorize(FACULTY, "mentee:view", resource=102, assigned_student_ids=assigned) is False


def test_faculty_mentee_check_without_db_or_context_is_denied():
    assert authorize(FACULTY, "student:view_gap", resource={"student_id": 101}) is False


def test_faculty_mentee_check_by_student_id_uses_mentor_assignment(db_session):
    assert authorize(FACULTY, "mentee:endorse", resource=101, db=db_session) is True
    assert authorize(FACULTY, "mentee:endorse", resource=102, db=db_session) is False


def test_faculty_mentee_check_by_user_id_resolves_the_student(db_session):
    assert authorize(FACULTY, "student:read", resource={"user_id": 3}, db=db_session) is True
    assert authorize(FACULTY, "student:read", resource={"user_id": 4}, db=db_session) is False
    # A user with no student row is never a mentee.
    assert authorize(FACULTY, "student:read", resource={"user_id": 999}, db=db_session) is False


def test_faculty_mentee_check_reads_ids_from_an_object_resource(db_session):
    mentee = SimpleNamespace(student_id=None, user_id=3)
    other = SimpleNamespace(student_id=102, user_id=None)
    assert authorize(FACULTY, "student:view_progress", resource=mentee, db=db_session) is True
    assert authorize(FACULTY, "student:view_progress", resource=other, db=db_session) is False


def test_faculty_manages_only_their_own_profile():
    assert authorize(FACULTY, "profile:read") is True
    assert authorize(FACULTY, "profile:update", resource={"user_id": 2}) is True
    assert authorize(FACULTY, "profile:update", resource={"user_id": 3}) is False
    assert authorize(FACULTY, "profile:read", resource=SimpleNamespace(user_id=2)) is True


def test_faculty_analytics_allowed_and_unlisted_actions_denied():
    assert authorize(FACULTY, "analytics:faculty") is True
    assert authorize(FACULTY, "analytics:admin") is False
    assert authorize(FACULTY, "progress:update") is False


# --- student --------------------------------------------------------------------


@pytest.mark.parametrize("action", ["catalogue:read", "catalogue:search", "resource:read"])
def test_student_reads_only_approved_catalogue_resources(action):
    assert authorize(STUDENT, action) is True
    assert authorize(STUDENT, action, resource={"moderation_state": "inactive"}) is False
    assert authorize(STUDENT, action, resource={"moderation_state": "approved"}) is True


@pytest.mark.parametrize("action", ["analytics:faculty", "analytics:admin", "audit:read"])
def test_student_blocked_from_analytics_and_audit(action):
    assert authorize(STUDENT, action) is False


def test_student_own_data_capability_check_without_a_resource():
    assert authorize(STUDENT, "roadmap:read") is True
    assert authorize(STUDENT, "gap:read") is True


def test_student_own_data_from_object_resource():
    assert authorize(STUDENT, "evidence:submit", resource=SimpleNamespace(user_id=3)) is True
    assert authorize(STUDENT, "evidence:submit", resource=SimpleNamespace(user_id=4)) is False


def test_student_id_without_db_falls_back_to_current_student_id_in_context():
    resource = {"student_id": 101}
    assert authorize(STUDENT, "progress:update", resource=resource, current_student_id=101) is True
    assert authorize(STUDENT, "progress:update", resource=resource, current_student_id=102) is False
    assert authorize(STUDENT, "progress:update", resource=resource) is False


def test_student_id_on_object_resource_checked_against_db(db_session):
    assert authorize(
        STUDENT, "roadmap:read", resource=SimpleNamespace(user_id=None, student_id=101),
        db=db_session,
    ) is True
    assert authorize(
        STUDENT, "roadmap:read", resource=SimpleNamespace(user_id=None, student_id=999),
        db=db_session,
    ) is False


def test_student_resource_without_any_owner_ids_is_allowed():
    """Current behaviour: a resource that names no owner is treated as a
    capability check. Pinned here so a change to it is deliberate."""
    assert authorize(STUDENT, "profile:read", resource={"title": "x"}) is True


def test_student_unlisted_action_is_denied():
    assert authorize(STUDENT, "catalogue:export") is False


# --- legacy dependency stub -----------------------------------------------------


def test_permissions_require_permission_stub_returns_a_noop_dependency():
    """backend.auth.dependencies.require_permission is the real one; this
    placeholder only has to build a callable that does nothing."""
    dependency = require_permission("profile:read")
    assert dependency(user=None, db=None) is None
