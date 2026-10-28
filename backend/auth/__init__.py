"""Authentication, authorization, and RBAC module for UpSkill-AI (Module 4)."""

from backend.auth.dependencies import get_current_user, require_role
from backend.auth.models import MentorAssignment, UserAccount, UserContext, UserRole
from backend.auth.permissions import authorize, require_permission
from backend.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.auth.views import auth_router

__all__ = [
    "UserAccount",
    "UserContext",
    "UserRole",
    "MentorAssignment",
    "authorize",
    "require_permission",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "require_role",
    "auth_router",
]
