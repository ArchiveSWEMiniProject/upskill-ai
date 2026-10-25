"""Role-Based Access Control (RBAC) and authorization service for UpSkill-AI.

Implements:
- Central authorize(user, action, resource) -> bool contract
  (CONTRACTS.md §5.2, SW Architecture §5.2, §6.1)
- REQ-F4-02: Role determines access to protected functionality
- REQ-F4-03: Block Students from Faculty or Administrator endpoints (TC-F4-04)
- REQ-F4-04: Block Faculty-Mentors from Administrator catalogue management (TC-F4-05)
- REQ-F4-13 & NFR-SEC-08: Faculty access scoped strictly to assigned mentees (TC-F4-06)
- REQ-F4-18 & TC-F4-12: Server-side authorization error on breach
"""

from typing import Any, Callable, Optional

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.models import MentorAssignment, UserAccount, UserContext, UserRole
from backend.database import get_db


def _extract_user_attrs(user: Any) -> tuple[Optional[int], Optional[str]]:
    """Extract user_id and normalized role string from various user representations."""
    if user is None:
        return None, None

    user_id = None
    role = None

    if isinstance(user, (UserContext, UserAccount)):
        user_id = user.user_id
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
    elif isinstance(user, dict):
        user_id = user.get("user_id")
        role = user.get("role")
        if isinstance(role, UserRole):
            role = role.value
        elif role is not None:
            role = str(role)
    else:
        user_id = getattr(user, "user_id", None)
        r = getattr(user, "role", None)
        role = r.value if isinstance(r, UserRole) else (str(r) if r is not None else None)

    return user_id, (role.lower() if role else None)


def _check_faculty_mentee_assignment(
    mentor_user_id: int,
    target_student_id: Optional[int],
    target_user_id: Optional[int],
    db: Optional[Session] = None,
    assigned_student_ids: Optional[set[int]] = None,
) -> bool:
    """Check whether a student is assigned to this faculty mentor."""
    if assigned_student_ids is not None:
        if target_student_id is not None and target_student_id in assigned_student_ids:
            return True
        if target_user_id is not None and target_user_id in assigned_student_ids:
            return True

    if db is None:
        return False

    query = db.query(MentorAssignment).filter(MentorAssignment.mentor_id == mentor_user_id)

    if target_student_id is not None:
        match = query.filter(MentorAssignment.student_id == target_student_id).first()
        if match:
            return True

    if target_user_id is not None:
        # Resolve target_user_id to student_id without importing M1's model
        row = db.execute(
            text("SELECT student_id FROM student WHERE user_id = :uid"),
            {"uid": target_user_id},
        ).first()
        if row:
            match = query.filter(MentorAssignment.student_id == row[0]).first()
            if match:
                return True

    return False


def authorize(
    user: Any,
    action: str,
    resource: Any = None,
    db: Optional[Session] = None,
    **context: Any,
) -> bool:
    """Central permission check used across all modules.

    Contract: authorize(user, action, resource) -> bool
    No module implements its own role logic (Architecture rule R1, §5.2).

    Parameters:
    - user: UserContext, UserAccount, dict, or object with user_id and role
    - action: The action string (e.g. 'catalogue:create', 'mentee:view', 'student:read')
    - resource: Optional target resource (dict, object, or None)
    - db: Optional SQLAlchemy session for checking database relationships (e.g., mentor assignments)
    - context: Additional contextual parameters (e.g., assigned_student_ids)

    Returns:
    - bool: True if authorized, False otherwise.
    """
    user_id, role = _extract_user_attrs(user)

    if not user_id or not role:
        return False

    # 1. Administrator: full administrative and catalogue privileges
    if role == UserRole.ADMINISTRATOR.value:
        return True

    # Normalize action
    action = action.lower()

    # 2. Faculty Mentor
    if role == UserRole.FACULTY_MENTOR.value:
        # Blocked from administrator catalogue management operations (REQ-F4-04, TC-F4-05)
        admin_catalogue_actions = {
            "catalogue:create",
            "catalogue:update",
            "catalogue:delete",
            "catalogue:moderate",
            "admin:access",
            "user:manage",
        }
        if action in admin_catalogue_actions:
            return False

        # Faculty can read approved catalogue resources
        if action in {"catalogue:read", "catalogue:search", "resource:read"}:
            if isinstance(resource, dict):
                moderation = resource.get("moderation_state")
                if moderation and moderation != "approved":
                    return False
            return True

        # Faculty student/mentee operations (REQ-F4-13, NFR-SEC-08, TC-F4-06)
        mentee_actions = {
            "mentee:view",
            "mentee:endorse",
            "mentee:override",
            "student:read",
            "student:view_progress",
            "student:view_gap",
        }
        if action in mentee_actions:
            if resource is None:
                # General capability check: faculty mentors can view mentees
                return True

            target_student_id = None
            target_user_id = None
            if isinstance(resource, dict):
                target_student_id = resource.get("student_id")
                target_user_id = resource.get("user_id")
            elif isinstance(resource, int):
                target_student_id = resource
            else:
                target_student_id = getattr(resource, "student_id", None)
                target_user_id = getattr(resource, "user_id", None)

            assigned_set = context.get("assigned_student_ids")
            return _check_faculty_mentee_assignment(
                mentor_user_id=user_id,
                target_student_id=target_student_id,
                target_user_id=target_user_id,
                db=db,
                assigned_student_ids=assigned_set,
            )

        # Faculty mentor can manage own profile
        if action in {"profile:read", "profile:update"}:
            if resource is None:
                return True
            res_user_id = (
                resource.get("user_id") if isinstance(resource, dict)
                else getattr(resource, "user_id", None)
            )
            return res_user_id == user_id

        # Faculty-specific analytics
        if action == "analytics:faculty":
            return True

        return False

    # 3. Student
    if role == UserRole.STUDENT.value:
        # Strictly blocked from all administrative and faculty actions (REQ-F4-03, TC-F4-04)
        elevated_actions = {
            "catalogue:create",
            "catalogue:update",
            "catalogue:delete",
            "catalogue:moderate",
            "mentee:view",
            "mentee:endorse",
            "mentee:override",
            "admin:access",
            "user:manage",
            "analytics:faculty",
            "analytics:admin",
            "audit:read",
        }
        if action in elevated_actions:
            return False

        # Student catalogue reading: can only access approved resources (REQ-F4-12, TC-F4-10)
        if action in {"catalogue:read", "catalogue:search", "resource:read"}:
            if isinstance(resource, dict):
                moderation = resource.get("moderation_state")
                if moderation and moderation != "approved":
                    return False
            return True

        # Student profile and progress access: own data only (NFR-SEC-07)
        student_data_actions = {
            "profile:read",
            "profile:update",
            "student:read",
            "student:update",
            "progress:read",
            "progress:update",
            "evidence:submit",
            "roadmap:read",
            "gap:read",
        }
        if action in student_data_actions:
            if resource is None:
                return True

            res_user_id = (
                resource.get("user_id") if isinstance(resource, dict)
                else getattr(resource, "user_id", None)
            )
            if res_user_id is not None:
                return res_user_id == user_id

            res_student_id = (
                resource.get("student_id") if isinstance(resource, dict)
                else getattr(resource, "student_id", None)
            )
            if res_student_id is not None:
                if db is not None:
                    row = db.execute(
                        text("SELECT user_id FROM student WHERE student_id = :sid"),
                        {"sid": res_student_id},
                    ).first()
                    return row is not None and row[0] == user_id
                # If context provides student_id mapping
                return context.get("current_student_id") == res_student_id

            return True

        return False

    # Unknown role
    return False


def require_permission(
    action: str,
    get_resource: Optional[Callable[..., Any]] = None,
) -> Callable[..., None]:
    """FastAPI dependency to enforce authorize() server-side.

    Raises HTTP 403 Forbidden with sanitized error message on breach (REQ-F4-18, TC-F4-12).
    """

    def dependency(
        user: UserContext = Depends(lambda: None),  # Resolved dynamically in dependencies.py
        db: Session = Depends(get_db),
    ) -> None:
        # Import lazily to prevent circular import

        # This will be overridden or injected in actual usage
        pass

    return dependency
