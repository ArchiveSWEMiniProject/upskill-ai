from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dashboard.schemas import DashboardRead
from backend.dashboard.service import DashboardService
from backend.database import get_db
from backend.progress.auth_placeholder import current_student_id

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/progress", response_model=DashboardRead)
def progress_dashboard(
    student_id: str = Depends(current_student_id), db: Session = Depends(get_db)
):
    return DashboardService(db).get(student_id)
