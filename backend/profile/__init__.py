"""Public identity lookup for consumers of M1 student profiles."""

from sqlalchemy.orm import Session

from backend.profile.repository import StudentRepository


def get_student_id(user_id: int, db: Session) -> int | None:
    """Resolve an authenticated account to a profile without exposing M1 models."""
    student = StudentRepository(db).get_by_user_id(user_id)
    return student.student_id if student is not None else None
