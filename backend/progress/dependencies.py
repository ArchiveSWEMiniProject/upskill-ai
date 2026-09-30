from fastapi import Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.progress.adapters import (
    UnavailableLearningCatalogue,
    UnavailableRecommendations,
    UnavailableSkillVector,
)
from backend.progress.service import ProgressService


def get_service(db: Session = Depends(get_db)) -> ProgressService:
    return ProgressService(
        db=db,
        catalogue=UnavailableLearningCatalogue(),
        skill_vector=UnavailableSkillVector(),
        recommendations=UnavailableRecommendations(),
    )
