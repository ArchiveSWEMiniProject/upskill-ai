class ProfileError(Exception):
    """Base class for M1 profile errors."""


class ProfileAlreadyExistsError(ProfileError):
    """The account already has a profile (REQ-F1-01: exactly one per account)."""

    message = "Profile already exists"


class ProfileNotFoundError(ProfileError):
    """The account has not created a profile yet."""

    message = "Profile not found"


class ProfileItemNotFoundError(ProfileError):
    """No such entry on the caller's profile (it may belong to someone else)."""

    message = "Entry not found"


class ResumeNotFoundError(ProfileError):
    """No such upload on the caller's profile (it may belong to someone else)."""

    message = "Resume not found"
