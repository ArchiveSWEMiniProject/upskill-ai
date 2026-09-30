from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.config import settings
from backend.evidence.models import CompletionEvidence
from backend.evidence.repository import EvidenceRepository
from backend.evidence.schemas import EvidenceCreate, EvidenceRead
from backend.progress.auth_placeholder import current_student_id
from backend.progress.dependencies import get_service
from backend.progress.enums import EvidenceType
from backend.progress.exceptions import NotFoundError
from backend.progress.schemas import CompletionRead, EnrolmentCreate, ProgressRead, ProgressUpdate
from backend.progress.service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("/enrolments", response_model=ProgressRead, status_code=status.HTTP_201_CREATED)
def enrol(
    body: EnrolmentCreate,
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    return service.enrol(student_id, body.resource_id)


@router.get("/enrolments", response_model=list[ProgressRead])
def enrolments(
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    return service.list_enrolments(student_id)


@router.patch("/enrolments/{progress_id}", response_model=ProgressRead)
def update_progress(
    progress_id: int,
    body: ProgressUpdate,
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    return service.update_progress(student_id, progress_id, body.completion_percentage)


@router.post("/enrolments/{progress_id}/evidence", response_model=EvidenceRead, status_code=201)
def submit_evidence(
    progress_id: int,
    body: EvidenceCreate,
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    return service.add_evidence(student_id, progress_id, body)


@router.post(
    "/enrolments/{progress_id}/evidence/file", response_model=EvidenceRead, status_code=201
)
async def upload_certificate(
    progress_id: int,
    file: UploadFile = File(...),
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    filename = file.filename or ""
    if file.content_type != "application/pdf" or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF certificate files are accepted")
    payload = await file.read(settings.max_evidence_bytes + 1)
    if len(payload) > settings.max_evidence_bytes:
        raise HTTPException(
            status_code=413, detail="Evidence file exceeds the configured size limit"
        )
    if not payload.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid PDF")
    file_key = f"{uuid4().hex}.pdf"
    storage_dir = Path(settings.evidence_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    destination = storage_dir / file_key
    destination.write_bytes(payload)
    try:
        return service.add_evidence(
            student_id,
            progress_id,
            EvidenceCreate(
                evidence_type=EvidenceType.CERTIFICATE,
                evidence_url=f"/api/v1/progress/evidence-files/{file_key}",
            ),
            file_key=file_key,
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise


@router.get("/enrolments/{progress_id}/evidence", response_model=list[EvidenceRead])
def evidence(
    progress_id: int,
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    progress = service.repo.by_id(progress_id, student_id)
    if progress is None:
        raise NotFoundError("Enrolment does not exist")
    return EvidenceRepository(service.db).list_for_progress(progress_id)


@router.get("/evidence-files/{file_key}")
def get_certificate(
    file_key: str,
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    evidence = service.db.query(CompletionEvidence).filter_by(file_key=file_key).first()
    if evidence is None or service.repo.by_id(evidence.progress_id, student_id) is None:
        raise NotFoundError("Evidence does not exist")
    path = Path(settings.evidence_storage_dir) / file_key
    if not path.is_file():
        raise NotFoundError("Evidence file does not exist")
    return FileResponse(path, media_type="application/pdf", filename="completion-evidence.pdf")


@router.post("/enrolments/{progress_id}/complete", response_model=CompletionRead)
def complete(
    progress_id: int,
    student_id: str = Depends(current_student_id),
    service: ProgressService = Depends(get_service),
):
    return service.complete(student_id, progress_id)
