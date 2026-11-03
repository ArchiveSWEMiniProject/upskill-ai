"""Authentication endpoints for UpSkill-AI.

Implements:
- REQ-F4-01: Authenticate Students, Faculty-Mentors, Administrators (TC-F4-01, TC-F4-02)
- REQ-F4-02: Assign role on authentication
- NFR-SEC-03: Argon2id password hashing on registration (TC-F4-03)
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.models import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserAccount,
    UserContext,
    UserResponse,
    UserRole,
)
from backend.auth.security import create_access_token, hash_password, verify_password
from backend.database import get_db

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT token",
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate student, faculty mentor, or administrator with email and password.

    Complies with:
    - TC-F4-01: Valid login issues a token and grants access.
    - TC-F4-02: Invalid password or email is rejected without revealing which field was wrong.
    """
    generic_auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    normalized_email = credentials.email.strip().lower()
    user = db.query(UserAccount).filter(UserAccount.email == normalized_email).first()

    # Check a password either way, so an unknown email takes as long as a wrong
    # password and response timing does not reveal which emails are registered.
    stored_hash = user.password_hash if user else _dummy_hash()
    if not verify_password(credentials.password, stored_hash) or not user:
        raise generic_auth_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token_payload = {
        "sub": str(user.user_id),
        "user_id": user.user_id,
        "email": user.email,
        "role": role_str,
    }
    token = create_access_token(data=token_payload)

    user_response = UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=UserRole(role_str),
        is_active=user.is_active,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_response,
    )


@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_current_user_profile(
    current_user: UserContext = Depends(get_current_user),
) -> UserResponse:
    """Return the profile for the currently authenticated user (TC-F4-01)."""
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account with Argon2id password hash",
)
def register(
    user_in: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Public sign-up (UP-1, REQ-F4-01). Always creates a student account.

    - Asking for any other role is refused (403): faculty and administrator
      accounts are created by an administrator, never by self-registration.
    - The email must be well-formed and the password must meet the strength
      rule (422 otherwise).
    - Only the user account is created here. The student profile belongs to
      M1 (architecture rule R4) and is created with POST /api/v1/profile.
    - TC-F4-03: the password is stored as an Argon2id hash, never in plaintext.
    """
    if user_in.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration creates student accounts only",
        )
    duplicate = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="A user with this email already exists",
    )
    if db.query(UserAccount).filter(UserAccount.email == user_in.email).first():
        raise duplicate

    new_user = UserAccount(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:  # a concurrent registration with the same email won
        db.rollback()
        raise duplicate from None
    db.refresh(new_user)

    return UserResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        role=UserRole.STUDENT,
        is_active=new_user.is_active,
    )


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password("timing-equaliser-not-a-real-password-1")
