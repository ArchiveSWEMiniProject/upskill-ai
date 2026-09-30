from enum import StrEnum


class ProgressStatus(StrEnum):
    ENROLLED = "enrolled"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"


class EvidenceType(StrEnum):
    CERTIFICATE = "certificate"
    QUIZ = "quiz"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
