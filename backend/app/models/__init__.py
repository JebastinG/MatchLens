import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ANALYSIS_STATUSES = ("queued", "processing", "completed", "failed")
EVIDENCE_STATUSES = (
    "supported",
    "needs_better_evidence",
    "related_skill_found",
    "no_evidence_found",
    "uncertain",
)


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


def _fk(target: str) -> ForeignKey:
    return ForeignKey(target, ondelete="CASCADE")


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (CheckConstraint(_in("status", ANALYSIS_STATUSES), name="ck_analysis_status"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(32), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    resume_filename: Mapped[str | None] = mapped_column(String(255))
    resume_page_count: Mapped[int | None] = mapped_column(Integer)
    github_url: Mapped[str | None] = mapped_column(String(500))
    analysis_mode: Mapped[str | None] = mapped_column(String(16))  # deterministic | llm
    llm_model: Mapped[str | None] = mapped_column(String(100))
    embedding_backend: Mapped[str | None] = mapped_column(String(64))
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped["JobDescription"] = relationship(
        back_populates="analysis", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )


class JobDescription(Base):
    __tablename__ = "job_descriptions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(_fk("analyses.id"), unique=True)
    mode: Mapped[str] = mapped_column(String(16))
    title: Mapped[str | None] = mapped_column(String(300))
    company: Mapped[str | None] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(2000))
    text: Mapped[str] = mapped_column(Text)
    analysis: Mapped[Analysis] = relationship(back_populates="job")


class JobRequirement(Base):
    __tablename__ = "job_requirements"
    __table_args__ = (UniqueConstraint("analysis_id", "ordinal", name="uq_req_ordinal"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(_fk("analyses.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(16), default="unspecified")
    key_terms: Mapped[list] = mapped_column(JSON, default=list)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (UniqueConstraint("analysis_id", "ref", name="uq_evidence_ref"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(_fk("analyses.id"), index=True)
    ref: Mapped[str] = mapped_column(String(200))  # stable identifier within the analysis
    source_type: Mapped[str] = mapped_column(String(16))  # resume | github
    text: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    repo: Mapped[str | None] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(2000))
    path: Mapped[str | None] = mapped_column(String(1000))
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequirementAssessment(Base):
    __tablename__ = "requirement_assessments"
    __table_args__ = (CheckConstraint(_in("status", EVIDENCE_STATUSES), name="ck_assessment_status"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(_fk("analyses.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(_fk("job_requirements.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32))
    explanation: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(16))  # deterministic | llm | reconciled
    confidence: Mapped[float | None] = mapped_column(Float)  # intentionally never populated
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)


class AssessmentEvidence(Base):
    __tablename__ = "assessment_evidence"
    __table_args__ = (Index("ix_ae_evidence", "evidence_id"),)
    assessment_id: Mapped[str] = mapped_column(_fk("requirement_assessments.id"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(_fk("evidence_items.id"), primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    quote: Mapped[str | None] = mapped_column(Text)  # verified substring of the evidence text


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(_fk("analyses.id"), index=True)
    requirement_id: Mapped[str | None] = mapped_column(_fk("job_requirements.id"))
    kind: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(_fk("analyses.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(_fk("job_requirements.id"))
    question: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), default="template")
