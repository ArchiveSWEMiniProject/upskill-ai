"""Faculty mentor endpoints for UpSkill-AI (Module 4).

Implements:
- CA-6: Faculty mentee view (REQ-F4-13, REQ-F1-40, NFR-SEC-08, TC-F4-06)
- List assigned mentees and view detailed mentee profile, skills, and progress
- Read-only protection for mentee records
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.models import (
    MenteeDetailResponse,
    MenteeItemSummary,
    MenteeSkillSummary,
    MenteeSummaryResponse,
    UserContext,
    UserRole,
)
from backend.auth.permissions import authorize
from backend.database import get_db
from backend.skills.vector import get_skill_vector

faculty_router = APIRouter(prefix="/api/v1/faculty", tags=["faculty"])


@faculty_router.get(
    "/mentees",
    response_model=list[MenteeSummaryResponse],
    summary="List all assigned mentees (Faculty mentor only)",
)
def list_assigned_mentees(
    limit: int = 50,
    offset: int = 0,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MenteeSummaryResponse]:
    """List all students assigned to the calling faculty mentor.

    Complies with:
    - REQ-F4-13: Faculty can view assigned mentees.
    - NFR-SEC-08: Access restricted strictly to assigned mentees.
    - Non-faculty/non-admin roles are rejected with 403.
    """
    if not authorize(current_user, "mentee:view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only faculty mentors can view mentee lists",
        )

    # Administrators can see all assignments; faculty mentors see only their own
    base_query = (
        "SELECT s.student_id, s.user_id, s.name, s.education_level, s.target_role_id, "
        "u.email, cr.role_name AS target_role_name, ma.assigned_at "
        "FROM mentor_assignment ma "
        "JOIN student s ON s.student_id = ma.student_id "
        "JOIN user_account u ON u.user_id = s.user_id "
        "LEFT JOIN career_role cr ON cr.role_id = s.target_role_id"
    )
    if current_user.role == UserRole.ADMINISTRATOR:
        query = text(f"{base_query} ORDER BY s.student_id ASC LIMIT :limit OFFSET :offset")
        params = {"limit": limit, "offset": offset}
    else:
        query = text(
            f"{base_query} WHERE ma.mentor_id = :mentor_id ORDER BY s.student_id ASC "
            "LIMIT :limit OFFSET :offset"
        )
        params = {"mentor_id": current_user.user_id, "limit": limit, "offset": offset}

    rows = db.execute(query, params).mappings().all()

    return [
        MenteeSummaryResponse(
            student_id=r["student_id"],
            user_id=r["user_id"],
            name=r["name"],
            email=r["email"],
            education_level=r["education_level"],
            target_role_id=r["target_role_id"],
            target_role_name=r["target_role_name"],
            assigned_at=r["assigned_at"],
        )
        for r in rows
    ]


@faculty_router.get(
    "/mentees/{student_id}",
    response_model=MenteeDetailResponse,
    summary="View assigned mentee's progress and details (Faculty mentor only)",
)
def get_mentee_details(
    student_id: int,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MenteeDetailResponse:
    """View assigned mentee profile, skills, and progress.

    Complies with:
    - TC-F4-06: Faculty mentor cannot view a student who is not their assigned mentee (returns 403).
    - REQ-F1-40: Mentee profile is read-only to faculty.
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
                "SELECT s.student_id, s.user_id, s.name, s.education_level, s.target_role_id, "
                "u.email, cr.role_name AS target_role_name, ma.assigned_at "
                "FROM student s "
                "JOIN user_account u ON u.user_id = s.user_id "
                "LEFT JOIN career_role cr ON cr.role_id = s.target_role_id "
                "LEFT JOIN mentor_assignment ma ON ma.student_id = s.student_id "
                "WHERE s.student_id = :sid"
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

    # Fetch the student's unified skill vector using M1's published interface (REQ-F1-27, R1/R2)
    try:
        vector = get_skill_vector(student_id, db)
        skills = [
            MenteeSkillSummary(
                skill_id=entry.canonical_skill_id,
                skill_name=entry.canonical_skill_name,
                level=entry.level.value if hasattr(entry.level, "value") else str(entry.level),
                source=entry.source.value if hasattr(entry.source, "value") else str(entry.source),
            )
            for entry in vector
        ]
    except Exception:
        skills = []

    items_rows = (
        db.execute(
            text(
                "SELECT profile_item_id AS item_id, item_type, title, description, "
                "grade, completion_term "
                "FROM profile_item "
                "WHERE student_id = :sid "
                "ORDER BY created_at DESC"
            ),
            {"sid": student_id},
        )
        .mappings()
        .all()
    )
    items = [
        MenteeItemSummary(
            item_id=ir["item_id"],
            item_type=str(ir["item_type"]),
            title=ir["title"],
            description=ir["description"],
            grade=ir["grade"],
            completion_term=ir["completion_term"],
        )
        for ir in items_rows
    ]

    return MenteeDetailResponse(
        student_id=row["student_id"],
        user_id=row["user_id"],
        name=row["name"],
        email=row["email"],
        education_level=row["education_level"],
        target_role_id=row["target_role_id"],
        target_role_name=row["target_role_name"],
        assigned_at=row["assigned_at"],
        skills=skills,
        profile_items=items,
    )

