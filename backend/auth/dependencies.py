"""FastAPI dependencies for authentication, token extraction, and RBAC authorization."""

from typing import Any, Callable, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.auth.models import UserAccount, UserContext, UserRole
from backend.auth.permissions import authorize
from backend.auth.security import decode_access_token
from backend.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserContext:
    """Extract and validate the current authenticated user from JWT Bearer token.

    Complies with:
    - NFR-SEC-01 (Authentication required for protected resources)
    - NFR-SEC-10 (Sanitized error responses, no credential leaks)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id_val = payload.get("sub") or payload.get("user_id")
        role_str = payload.get("role")
        if user_id_val is None or role_str is None:
            raise credentials_exception
        user_id = int(user_id_val)
        _ = UserRole(role_str)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_exception from None

    user_record = db.query(UserAccount).filter(UserAccount.user_id == user_id).first()
    if not user_record or not user_record.is_active:
        raise credentials_exception

    role_val = (
        user_record.role.value if hasattr(user_record.role, "value")
        else user_record.role
    )
    role_enum = UserRole(role_val)
    return UserContext(
        user_id=user_record.user_id,
        email=user_record.email,
        role=role_enum,
        is_active=user_record.is_active,
    )


def require_role(*allowed_roles: UserRole) -> Callable[[UserContext], UserContext]:
    """Dependency factory restricting access to specific roles."""

    def role_checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: role not permitted",
            )
        return user

    return role_checker


def require_permission(
    action: str,
    resource_provider: Optional[Callable[..., Any]] = None,
) -> Callable[..., UserContext]:
    """Dependency factory enforcing M4's central authorize(user, action, resource).

    Complies with:
    - REQ-F4-03 (Block students from elevated endpoints)
    - REQ-F4-04 (Block faculty from admin catalogue operations)
    - REQ-F4-18 (Authorization error on breach)
    - NFR-SEC-02 (Server-side authorization enforcement)
    """

    def permission_checker(
        user: UserContext = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> UserContext:
        resource = resource_provider() if resource_provider else None
        is_allowed = authorize(user=user, action=action, resource=resource, db=db)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: unauthorized for action '{action}'",
            )
        return user

    return permission_checker
