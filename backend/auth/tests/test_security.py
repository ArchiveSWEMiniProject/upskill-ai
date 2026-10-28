"""Tests for Argon2id password hashing and JWT utilities (CA-2, NFR-SEC-03)."""

import jwt
import pytest

from backend.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_argon2id_hash_format():
    """Verify that hash_password uses Argon2id (TC-F4-03, NFR-SEC-03)."""
    password = "TestPass#2026"
    hashed = hash_password(password)

    # Argon2id produces hashes prefixed with $argon2id$
    assert hashed.startswith("$argon2id$")
    assert password not in hashed


def test_argon2id_verification():
    """Verify that correct password validates and incorrect password is rejected."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "") is False


def test_argon2id_empty_password_rejected():
    """Verify empty password raises ValueError."""
    with pytest.raises(ValueError):
        hash_password("")


def test_jwt_token_roundtrip():
    """Verify JWT token encoding and decoding."""
    payload = {"sub": "42", "email": "test@pes.edu", "role": "student"}
    token = create_access_token(payload)

    assert isinstance(token, str)
    decoded = decode_access_token(token)

    assert decoded["sub"] == "42"
    assert decoded["email"] == "test@pes.edu"
    assert decoded["role"] == "student"
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_invalid_token_rejected():
    """Verify invalid token raises PyJWTError."""
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("invalid.token.structure")
