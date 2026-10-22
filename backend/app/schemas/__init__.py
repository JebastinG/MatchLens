from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

EvidenceStatus = Literal[
    "supported", "needs_better_evidence", "related_skill_found", "no_evidence_found", "uncertain"
]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class AnalysisAccepted(BaseModel):
    id: str
    status: str
    created_at: datetime
    status_url: str
    results_url: str


class AnalysisStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    stage: str
    progress: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    warnings: list[str]
    analysis_mode: str | None
    llm_model: str | None
    embedding_backend: str | None
    resume_filename: str | None
    resume_page_count: int | None
    github_url: str | None


class EvidenceOut(BaseModel):
    id: str
    ref: str
    source_type: Literal["resume", "github"]
    text: str
    quote: str | None
    page_number: int | None
    repo: str | None
    source_url: str | None
    path: str | None
    line_start: int | None
    line_end: int | None
    commit_sha: str | None
    retrieved_at: datetime | None


class AssessmentOut(BaseModel):
    id: str
    status: EvidenceStatus
    explanation: str
    method: str
    confidence: None = None  # no calibrated confidence is produced
    warnings: list[str]
    dismissed: bool
    evidence: list[EvidenceOut]


class RequirementOut(BaseModel):
    id: str
    ordinal: int
    text: str
    category: str
    key_terms: list[str]
    assessment: AssessmentOut


class RecommendationOut(BaseModel):
    id: str
    requirement_id: str | None
    kind: str
    text: str


class QuestionOut(BaseModel):
    id: str
    requirement_id: str
    question: str
    rationale: str
    source: str


class SummaryOut(BaseModel):
    total_requirements: int
    dismissed: int
    counts: dict[str, int]
    direct_support_share: float | None
    evidence_coverage_share: float | None
    definitions: dict[str, str]
    disclaimer: str


class JobOut(BaseModel):
    mode: str
    title: str | None
    company: str | None
    source_url: str | None


class ResultsOut(BaseModel):
    analysis: AnalysisStatus
    job: JobOut
    summary: SummaryOut
    requirements: list[RequirementOut]
    recommendations: list[RecommendationOut]
    interview_questions: list[QuestionOut]


class DismissIn(BaseModel):
    dismissed: bool
