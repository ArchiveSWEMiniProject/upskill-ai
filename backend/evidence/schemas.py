"""Accept certificate link metadata or a self-assessment score."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class CertificateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_type: Literal["certificate"]
    evidence_url: HttpUrl

    @field_validator("evidence_url")
    @classmethod
    def check_link(cls, value: HttpUrl) -> HttpUrl:
        if len(str(value)) > 255 or value.username is not None or value.password is not None:
            raise ValueError("Use an HTTP(S) link of at most 255 characters without credentials")
        return value


class QuizIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_type: Literal["quiz"]
    score: int = Field(ge=0, le=100, strict=True)


EvidenceIn = Annotated[CertificateIn | QuizIn, Field(discriminator="evidence_type")]
