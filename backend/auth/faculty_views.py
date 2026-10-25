"""Faculty mentor endpoints for UpSkill-AI (Module 4).

Implements:
- REQ-F4-13: Faculty mentee view scoped by mentor_assignment (TC-F4-06)
- NFR-SEC-08: Access restricted strictly to assigned mentees
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.models import UserAccount, UserContext
from backend.auth.permissions import authorize
from backend.database import get_db

faculty_router = APIRouter(prefix="/api/v1/faculty", tags=["faculty"])


@faculty_router.get(
    "/mentees/{student_id}",
    summary="View assigned mentee's progress and details (Faculty mentor only)",
)
def get_mentee_details(
    student_id: int,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View assigned mentee details.

    Complies with:
    - TC-F4-06: Faculty mentor cannot view a student who is not their assigned mentee (returns 403).
    - NFR-SEC-08: Mentee scoping enforced server-side.
    """
    is_allowed = authorize(
        user=current_user,
        action="mentee:view",
        resource={"student_id": student_id},
        db=db,
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you can only view students assigned to you as mentees",
        )

    row = (
        db.execute(
            text(
                "SELECT student_id, user_id, name, education_level, target_role_id "
                "FROM student WHERE student_id = :sid"
            ),
            {"sid": student_id},
        )
        .mappings()
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found",
        )

    user_acc = db.query(UserAccount).filter(UserAccount.user_id == row["user_id"]).first()

    return {
        "student_id": row["student_id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "email": user_acc.email if user_acc else None,
        "education_level": row["education_level"],
        "target_role_id": row["target_role_id"],
    }
