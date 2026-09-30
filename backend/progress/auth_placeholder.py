from fastapi import Header, HTTPException


def current_student_id(x_student_id: str | None = Header(default=None)) -> str:
    """TEMPORARY DEVELOPMENT PLACEHOLDER — replace with M4 auth dependency."""
    if not x_student_id or not x_student_id.strip():
        raise HTTPException(status_code=401, detail="Authentication is required")
    return x_student_id.strip()
