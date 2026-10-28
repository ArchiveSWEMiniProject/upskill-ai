from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.dependencies import current_user_id, profile_service
from backend.profile.entries import CourseService, EntryService, ProjectService
from backend.profile.exceptions import (
    ProfileAlreadyExistsError,
    ProfileError,
    ProfileNotFoundError,
    ResumeNotFoundError,
)
from backend.profile.repository import ProfileItemRepository, StudentRepository
from backend.profile.resume import MAX_BYTES, ResumeRejected, ResumeService
from backend.profile.schemas import (
    CourseIn,
    CourseOut,
    ProfileCreate,
    ProfileOut,
    ProjectIn,
    ProjectOut,
    ResumeOut,
)
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


# --- Course and project entries (UP-3, UP-4) -------------------------------

NOT_FOUND = {404: {"description": "No profile yet, or no such entry on the caller's profile"}}


def _not_found(error: ProfileError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, error.message)


def add_entry_routes(path: str, service_type: type[EntryService], body_type, out_type) -> None:
    """GET/POST {path} and PUT/DELETE {path}/{entry_id} for one entry type."""
    label = service_type.item_type

    def service(session: Annotated[Session, Depends(get_session)]) -> EntryService:
        return service_type(StudentRepository(session), ProfileItemRepository(session))

    Service = Annotated[EntryService, Depends(service)]
    SessionDep = Annotated[Session, Depends(get_session)]

    @router.get(path, response_model=list[out_type], responses=NOT_FOUND,
                summary=f"List the caller's {label}s")
    def list_entries(user_id: UserId, entries: Service):
        try:
            return entries.list(user_id)
        except ProfileError as error:
            raise _not_found(error) from error

    @router.post(path, status_code=status.HTTP_201_CREATED, response_model=out_type,
                 responses=NOT_FOUND, summary=f"Add a {label}")
    def add_entry(body: body_type, user_id: UserId, entries: Service, session: SessionDep):
        try:
            entry = entries.add(user_id, body)
        except ProfileError as error:
            raise _not_found(error) from error
        session.commit()
        return entry

    @router.put(f"{path}/{{entry_id}}", response_model=out_type, responses=NOT_FOUND,
                summary=f"Edit a {label} (the body replaces every field)")
    def replace_entry(
        entry_id: int, body: body_type, user_id: UserId, entries: Service, session: SessionDep
    ):
        try:
            entry = entries.replace(user_id, entry_id, body)
        except ProfileError as error:
            raise _not_found(error) from error
        session.commit()
        return entry

    @router.delete(f"{path}/{{entry_id}}", status_code=status.HTTP_204_NO_CONTENT,
                   responses=NOT_FOUND, summary=f"Delete a {label}")
    def delete_entry(entry_id: int, user_id: UserId, entries: Service, session: SessionDep):
        try:
            entries.delete(user_id, entry_id)
        except ProfileError as error:
            raise _not_found(error) from error
        session.commit()


# REQ-F1-02, F1-35, F1-36
add_entry_routes("/courses", CourseService, CourseIn, CourseOut)
# REQ-F1-03, F1-37
add_entry_routes("/projects", ProjectService, ProjectIn, ProjectOut)


# --- Resume upload (UP-6) ------------------------------------------------------

MANUAL_ENTRY = "/api/v1/profile/skills"
RESUME_NOT_FOUND = {
    404: {"description": "No profile yet, or no such upload on the caller's profile"}
}
RESUME_ERRORS = {
    **RESUME_NOT_FOUND,
    413: {"description": "File exceeds the 5 MB limit."},
    415: {"description": "Only PDF and DOCX files are accepted."},
}


def _resume_out(upload, message: str | None = None) -> ResumeOut:
    return ResumeOut(
        upload_id=upload.upload_id,
        file_name=upload.original_filename,
        file_type=upload.file_type,
        size_bytes=upload.size_bytes,
        status=upload.status,
        message=message,
        manual_entry=MANUAL_ENTRY if upload.status != "extracted" else None,
        uploaded_at=upload.uploaded_at,
        delete_after=upload.delete_after,
        deleted=upload.deleted_at is not None,
    )


def _student_id(session: Session, user_id: int) -> int:
    student = StudentRepository(session).get_by_user_id(user_id)
    if student is None:
        raise _not_found(ProfileNotFoundError())
    return student.student_id


@router.post("/resume", status_code=status.HTTP_201_CREATED, response_model=ResumeOut,
             responses=RESUME_ERRORS)
async def upload_resume(
    user_id: UserId,
    session: Annotated[Session, Depends(get_session)],
    file: Annotated[UploadFile, File(description="PDF or DOCX, at most 5 MB")],
) -> ResumeOut:
    """Upload a resume (REQ-F1-08 to F1-11). The response's `status` says what
    happened: `extracted` (text found), `unreadable` (under 100 characters, so
    use manual entry instead) or `failed` (the file could not be processed;
    the profile is unchanged). Unusable files are not kept."""
    student_id = _student_id(session, user_id)
    data = await file.read(MAX_BYTES + 1)  # one byte over is enough to refuse
    try:
        result = ResumeService(session).upload(student_id, file.filename, data)
    except ResumeRejected as error:
        raise HTTPException(error.status_code, error.message) from error
    session.commit()
    return _resume_out(result.upload, result.message)


@router.get("/resume", response_model=list[ResumeOut], responses=RESUME_NOT_FOUND)
def list_resumes(user_id: UserId, session: Annotated[Session, Depends(get_session)]):
    """The caller's uploads, newest first, with their status and deletion date."""
    student_id = _student_id(session, user_id)
    return [_resume_out(upload) for upload in ResumeService(session).list(student_id)]


@router.get("/resume/{upload_id}", response_model=ResumeOut, responses=RESUME_NOT_FOUND)
def get_resume(
    upload_id: int, user_id: UserId, session: Annotated[Session, Depends(get_session)]
):
    upload = ResumeService(session).get(_student_id(session, user_id), upload_id)
    if upload is None:
        raise _not_found(ResumeNotFoundError())
    return _resume_out(upload)
