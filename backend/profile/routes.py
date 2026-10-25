from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.courses import CourseService
from backend.profile.dependencies import current_user_id, profile_service
from backend.profile.exceptions import (
    ProfileAlreadyExistsError,
    ProfileError,
    ProfileNotFoundError,
)
from backend.profile.repository import ProfileItemRepository, StudentRepository
from backend.profile.schemas import CourseIn, CourseOut, ProfileCreate, ProfileOut
from backend.profile.service import ProfileService

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

UserId = Annotated[int, Depends(current_user_id)]
Service = Annotated[ProfileService, Depends(profile_service)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileOut)
def create_profile(
    body: ProfileCreate,
    user_id: UserId,
    service: Service,
    session: Annotated[Session, Depends(get_session)],
) -> ProfileOut:
    """Create the caller's profile; an account may have exactly one (REQ-F1-01)."""
    try:
        student = service.create_profile(user_id, body.name, body.education_level)
    except ProfileAlreadyExistsError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.message) from error
    session.commit()
    return ProfileOut.model_validate(student)


@router.get("", response_model=ProfileOut)
def get_profile(user_id: UserId, service: Service) -> ProfileOut:
    """Return the caller's own profile; there is no way to name another one (REQ-F1-39)."""
    try:
        return ProfileOut.model_validate(service.get_profile(user_id))
    except ProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error


# --- Course entries (UP-3) ---------------------------------------------------


def course_service(session: Annotated[Session, Depends(get_session)]) -> CourseService:
    return CourseService(StudentRepository(session), ProfileItemRepository(session))


Courses = Annotated[CourseService, Depends(course_service)]
NOT_FOUND = {404: {"description": "No profile yet, or no such course on the caller's profile"}}


def _not_found(error: ProfileError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, error.message)


@router.get("/courses", response_model=list[CourseOut], responses=NOT_FOUND)
def list_courses(user_id: UserId, courses: Courses) -> list[CourseOut]:
    """The caller's course entries, oldest first."""
    try:
        return courses.list_courses(user_id)
    except ProfileError as error:
        raise _not_found(error) from error


@router.post(
    "/courses", status_code=status.HTTP_201_CREATED, response_model=CourseOut, responses=NOT_FOUND
)
def add_course(
    body: CourseIn,
    user_id: UserId,
    courses: Courses,
    session: Annotated[Session, Depends(get_session)],
) -> CourseOut:
    """Add a completed course (REQ-F1-02). Missing fields or a grade outside
    S-F / 0-100 return 422 naming the field, and nothing is saved (REQ-F1-35, F1-36)."""
    try:
        course = courses.add_course(user_id, body)
    except ProfileError as error:
        raise _not_found(error) from error
    session.commit()
    return course


@router.put("/courses/{course_id}", response_model=CourseOut, responses=NOT_FOUND)
def replace_course(
    course_id: int,
    body: CourseIn,
    user_id: UserId,
    courses: Courses,
    session: Annotated[Session, Depends(get_session)],
) -> CourseOut:
    """Edit a course: the body replaces every field."""
    try:
        course = courses.replace_course(user_id, course_id, body)
    except ProfileError as error:
        raise _not_found(error) from error
    session.commit()
    return course


@router.delete(
    "/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
def delete_course(
    course_id: int,
    user_id: UserId,
    courses: Courses,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    try:
        courses.delete_course(user_id, course_id)
    except ProfileError as error:
        raise _not_found(error) from error
    session.commit()
