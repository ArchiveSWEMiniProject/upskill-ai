from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.progress.enums import EvidenceType, VerificationStatus


class EvidenceCreate(BaseModel):
    evidence_type: EvidenceType
    evidence_url: str | None = Field(default=None, max_length=255)
    score: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def evidence_fields_match_type(self):
        if self.evidence_type == EvidenceType.QUIZ and self.score is None:
            raise ValueError("A quiz score is required for quiz evidence")
        if self.evidence_type == EvidenceType.CERTIFICATE and self.score is not None:
            raise ValueError("A certificate cannot include a quiz score")
        if self.evidence_type == EvidenceType.CERTIFICATE and not self.evidence_url:
            raise ValueError("Certificate metadata or an uploaded file is required")
        return self


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: int
    progress_id: int
    evidence_type: EvidenceType
    evidence_url: str | None
    score: int | None
    submitted_date: datetime
    verification_status: VerificationStatus
