"""Unit tests for central authorize(user, action, resource) -> bool contract (CA-1).

Complies with:
- CONTRACTS.md §5.2
- REQ-F4-02: Role-based permissions
- REQ-F4-03: Block student from elevated endpoints (TC-F4-04)
- REQ-F4-04: Block faculty from admin catalogue ops (TC-F4-05)
- REQ-F4-13 & NFR-SEC-08: Faculty mentee scoping (TC-F4-06)
"""

from backend.auth.models import UserContext, UserRole
from backend.auth.permissions import authorize


def test_admin_has_full_access(db_session):
    """Administrator is authorized for all actions."""
    admin = UserContext(user_id=1, email="admin@pes.edu", role=UserRole.ADMINISTRATOR)

    assert authorize(admin, "catalogue:create", db=db_session) is True
    assert authorize(admin, "catalogue:moderate", db=db_session) is True
    assert authorize(admin, "catalogue:delete", db=db_session) is True
    assert authorize(admin, "mentee:view", resource={"student_id": 101}, db=db_session) is True
    assert authorize(admin, "analytics:admin", db=db_session) is True


def test_student_blocked_from_elevated_actions(db_session):
    """Student is blocked from administrative and faculty endpoints (REQ-F4-03, TC-F4-04)."""
    student = UserContext(user_id=3, email="s1@pes.edu", role=UserRole.STUDENT)

    # Admin actions
    assert authorize(student, "catalogue:create", db=db_session) is False
    assert authorize(student, "catalogue:update", db=db_session) is False
    assert authorize(student, "catalogue:delete", db=db_session) is False
    assert authorize(student, "catalogue:moderate", db=db_session) is False
    assert authorize(student, "admin:access", db=db_session) is False

    # Faculty actions
    assert authorize(student, "mentee:view", resource={"student_id": 101}, db=db_session) is False
    assert authorize(student, "mentee:endorse", db=db_session) is False
    assert authorize(student, "mentee:override", db=db_session) is False


def test_student_can_only_access_own_profile(db_session):
    """Student can access their own profile/progress but not another student's (NFR-SEC-07)."""
    student = UserContext(user_id=3, email="s1@pes.edu", role=UserRole.STUDENT)

    # Own profile by user_id
    assert authorize(student, "profile:read", resource={"user_id": 3}, db=db_session) is True
    assert authorize(student, "profile:update", resource={"user_id": 3}, db=db_session) is True

    # Other student's profile by user_id
    assert authorize(student, "profile:read", resource={"user_id": 4}, db=db_session) is False
    assert authorize(student, "profile:update", resource={"user_id": 4}, db=db_session) is False

    # Own profile by student_id (student_id 101 belongs to user_id 3 in conftest)
    assert authorize(student, "progress:read", resource={"student_id": 101}, db=db_session) is True
    assert authorize(student, "progress:read", resource={"student_id": 102}, db=db_session) is False


def test_faculty_blocked_from_admin_catalogue_ops(db_session):
    """Faculty mentor is blocked from admin catalogue operations (REQ-F4-04, TC-F4-05)."""
    faculty = UserContext(user_id=2, email="faculty@pes.edu", role=UserRole.FACULTY_MENTOR)

    assert authorize(faculty, "catalogue:create", db=db_session) is False
    assert authorize(faculty, "catalogue:moderate", db=db_session) is False
    assert authorize(faculty, "catalogue:delete", db=db_session) is False
    assert authorize(faculty, "admin:access", db=db_session) is False


def test_faculty_mentee_scoping(db_session):
    """Faculty mentor can view assigned mentee but not unassigned students (TC-F4-06)."""
    faculty = UserContext(user_id=2, email="faculty@pes.edu", role=UserRole.FACULTY_MENTOR)

    # Student 101 is assigned to Faculty 2 in conftest
    assert authorize(faculty, "mentee:view", resource={"student_id": 101}, db=db_session) is True
    res101 = {"student_id": 101}
    assert authorize(faculty, "student:view_progress", resource=res101, db=db_session) is True

    # Student 102 is unassigned
    assert authorize(faculty, "mentee:view", resource={"student_id": 102}, db=db_session) is False
    res102 = {"student_id": 102}
    assert authorize(faculty, "student:view_progress", resource=res102, db=db_session) is False


def test_unauthenticated_user_denied(db_session):
    """Anonymous or None user is denied across all operations."""
    assert authorize(None, "catalogue:read", db=db_session) is False
    assert authorize({}, "catalogue:read", db=db_session) is False
    assert authorize(None, "mentee:view", db=db_session) is False
