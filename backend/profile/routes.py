from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.profile.dependencies import current_user_id, profile_service
from backend.profile.entries import CourseService, EntryService, ProjectService
from backend.profile.exceptions import (
    ProfileAlreadyExistsError,
    ProfileError,
    ProfileNotFoundError,
    ResumeNotFoundError,
    UnknownRoleError,
)
from backend.profile.extracted_schemas import (
    BulkConfirmOut,
    ExtractedSkillOut,
    ExtractedSkillsOut,
    SkillDecisionOut,
    SkillDecisionsIn,
)
from backend.profile.extracted_skills import (
    CandidateAlreadyDecidedError,
    CandidateNotFoundError,
    Decision,
    ExtractedSkillService,
    high_confidence_threshold,
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
    RoleOut,
    TargetRoleIn,
    TargetRoleOut,
)
from backend.profile.service import ProfileService
from backend.profile.target_role import TargetRoleService

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


def _resume_out(upload, message: str | None = None, skills_found: int | None = None) -> ResumeOut:
    return ResumeOut(
        upload_id=upload.upload_id,
        file_name=upload.original_filename,
        file_type=upload.file_type,
        size_bytes=upload.size_bytes,
        status=upload.status,
        message=message,
        manual_entry=MANUAL_ENTRY if upload.status != "extracted" or skills_found == 0 else None,
        uploaded_at=upload.uploaded_at,
        delete_after=upload.delete_after,
        deleted=upload.deleted_at is not None,
        skills_found=skills_found,
    )


def _student_id(session: Session, user_id: int) -> int:
    student = StudentRepository(session).get_by_user_id(user_id)
    if student is None:
        raise _not_found(ProfileNotFoundError())
    return student.student_id


@router.post("/resume", status_code=status.HTTP_201_CREATED, response_model=ResumeOut,
             responses=RESUME_ERRORS)
def upload_resume(
    user_id: UserId,
    session: Annotated[Session, Depends(get_session)],
    file: Annotated[UploadFile, File(description="PDF or DOCX, at most 5 MB")],
) -> ResumeOut:
    """Upload a resume (REQ-F1-08 to F1-11). The response's `status` says what
    happened: `extracted` (text found), `unreadable` (under 100 characters, so
    use manual entry instead) or `failed` (the file could not be processed;
    the profile is unchanged). Unusable files are not kept."""
    # A plain def, so FastAPI runs it in its thread pool: parsing a PDF and the
    # database calls block, and on the event loop they would stall every request.
    student_id = _student_id(session, user_id)
    data = file.file.read(MAX_BYTES + 1)  # one byte over is enough to refuse
    try:
        result = ResumeService(session).upload(student_id, file.filename, data)
    except ResumeRejected as error:
        raise HTTPException(error.status_code, error.message) from error
    try:
        session.commit()
    except Exception:
        ResumeService.discard(result.upload)
        raise
    return _resume_out(result.upload, result.message, result.skills_found)


@router.get("/resume", response_model=list[ResumeOut], responses=RESUME_NOT_FOUND)
def list_resumes(user_id: UserId, session: Annotated[Session, Depends(get_session)]):
    """The caller's uploads, newest first, with their status and deletion date."""
    student_id = _student_id(session, user_id)
    return [_resume_out(upload) for upload in ResumeService(session).list(student_id)]


@router.get("/resume/extracted", response_model=ExtractedSkillsOut, responses=NOT_FOUND)
def list_extracted_skills(
    user_id: UserId,
    session: Annotated[Session, Depends(get_session)],
    min_confidence: Annotated[float | None, Query(ge=0, le=1)] = None,
    upload_id: int | None = None,
    status_filter: Annotated[
        Literal["pending", "confirmed", "rejected", "all"], Query(alias="status")
    ] = "pending",
) -> ExtractedSkillsOut:
    """Skills found in the caller's resumes, highest confidence first, each with
    its confidence and the sentence it came from (REQ-F1-13, F1-14). Pending
    ones by default; none of them is on the profile until confirmed."""
    found = ExtractedSkillService(session).candidates(
        _student_id(session, user_id),
        status=None if status_filter == "all" else status_filter,
        min_confidence=None if min_confidence is None else Decimal(str(min_confidence)),
        upload_id=upload_id,
    )
    return ExtractedSkillsOut(
        threshold=float(high_confidence_threshold()),
        candidates=[
            ExtractedSkillOut(**{**vars(c), "confidence": float(c.confidence)}) for c in found
        ],
    )


@router.get("/resume/{upload_id}", response_model=ResumeOut, responses=RESUME_NOT_FOUND)
def get_resume(
    upload_id: int, user_id: UserId, session: Annotated[Session, Depends(get_session)]
):
    upload = ResumeService(session).get(_student_id(session, user_id), upload_id)
    if upload is None:
        raise _not_found(ResumeNotFoundError())
    return _resume_out(upload)


# --- Target role (UP-13) -----------------------------------------------------


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    user_id: UserId, session: Annotated[Session, Depends(get_session)]
) -> list[RoleOut]:
    """The roles a student can pick as their target (REQ-F1-31)."""
    return [
        RoleOut(role_id=role_id, role_name=name)
        for role_id, name in TargetRoleService(session).list_roles()
    ]


@router.put(
    "/target-role",
    response_model=TargetRoleOut,
    responses={404: {"description": "No profile yet"}, 422: {"description": "Unknown role"}},
)
def set_target_role(
    body: TargetRoleIn, user_id: UserId, session: Annotated[Session, Depends(get_session)]
) -> TargetRoleOut:
    """Choose the caller's one active target role, replacing any earlier one
    (REQ-F1-31, F1-32). A change marks recommendations stale (REQ-F1-33); the
    reply counts required, held and gap skills (REQ-F1-34)."""
    try:
        summary = TargetRoleService(session).set_target_role(user_id, body.role_id)
    except ProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    except UnknownRoleError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.message) from error
    session.commit()
    return TargetRoleOut.model_validate(summary)


@router.get(
    "/target-role",
    response_model=TargetRoleOut,
    responses={404: {"description": "No profile yet, or no target role chosen"}},
)
def get_target_role(
    user_id: UserId, session: Annotated[Session, Depends(get_session)]
) -> TargetRoleOut:
    """The caller's current target role with its required/held/gap counts."""
    try:
        summary = TargetRoleService(session).get_target_role(user_id)
    except ProfileNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    if summary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No target role chosen")
    return TargetRoleOut.model_validate(summary)


# --- Extracted resume skills (UP-7, UP-8) -------------------------------------


def _decision_out(outcome) -> SkillDecisionOut:
    return SkillDecisionOut(
        candidate_id=outcome.candidate_id,
        skill_id=outcome.skill_id,
        skill_name=outcome.skill_name,
        status=outcome.status,
        level=outcome.level,
    )


@router.post(
    "/skills/confirm",
    response_model=list[SkillDecisionOut],
    responses={
        404: {"description": "No profile, or no such extracted skill on it"},
        409: {"description": "An extracted skill was already confirmed or rejected"},
    },
)
def decide_extracted_skills(
    body: SkillDecisionsIn, user_id: UserId, session: Annotated[Session, Depends(get_session)]
) -> list[SkillDecisionOut]:
    """Confirm (optionally at an edited level) or reject extracted skills, one
    decision each (REQ-F1-15, F1-16). All of them apply, or none do."""
    student_id = _student_id(session, user_id)
    decisions = [Decision(d.candidate_id, d.action, d.level) for d in body.decisions]
    try:
        outcomes = ExtractedSkillService(session).decide(student_id, decisions)
    except CandidateNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from error
    except CandidateAlreadyDecidedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.message) from error
    session.commit()
    return [_decision_out(outcome) for outcome in outcomes]


@router.post("/skills/confirm-high-confidence", response_model=BulkConfirmOut,
             responses=NOT_FOUND)
def confirm_high_confidence_skills(
    user_id: UserId, session: Annotated[Session, Depends(get_session)]
) -> BulkConfirmOut:
    """Confirm in one action every pending extracted skill whose confidence is
    at or above the configured threshold (REQ-F1-17)."""
    threshold, outcomes = ExtractedSkillService(session).confirm_high_confidence(
        _student_id(session, user_id)
    )
    session.commit()
    return BulkConfirmOut(
        threshold=float(threshold), confirmed=[_decision_out(o) for o in outcomes]
    )
