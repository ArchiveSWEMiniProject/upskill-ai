"""Authentication endpoints for UpSkill-AI.

Implements:
- REQ-F4-01: Authenticate Students, Faculty-Mentors, Administrators (TC-F4-01, TC-F4-02)
- REQ-F4-02: Assign role on authentication
- NFR-SEC-03: Argon2id password hashing on registration (TC-F4-03)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
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

    if not user:
        raise generic_auth_exception

    if not verify_password(credentials.password, user.password_hash):
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
    """Register a new user account.

    Complies with:
    - TC-F4-03: Stored passwords are never held in plaintext, using Argon2id.
    """
    normalized_email = user_in.email.strip().lower()
    existing_user = db.query(UserAccount).filter(UserAccount.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    # Argon2id password hash (never stored or logged in plaintext)
    hashed_password = hash_password(user_in.password)

    new_user = UserAccount(
        email=normalized_email,
        password_hash=hashed_password,
        role=user_in.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # If role is student, create student row
    if new_user.role == UserRole.STUDENT:
        student_name = user_in.name.strip() if user_in.name else user_in.email.split("@")[0]
        db.execute(
            text("INSERT INTO student (user_id, name) VALUES (:uid, :name)"),
            {"uid": new_user.user_id, "name": student_name},
        )
        db.commit()

    role_str = new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role)
    return UserResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        role=UserRole(role_str),
        is_active=new_user.is_active,
    )
