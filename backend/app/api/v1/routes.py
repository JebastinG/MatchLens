import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models import (
    EVIDENCE_STATUSES,
    Analysis,
    AssessmentEvidence,
    EvidenceItem,
    InterviewQuestion,
    JobDescription,
    JobRequirement,
    Recommendation,
    RequirementAssessment,
    new_id,
)
from app.schemas import (
    AnalysisAccepted,
    AnalysisStatus,
    AssessmentOut,
    DismissIn,
    EvidenceOut,
    JobOut,
    QuestionOut,
    RecommendationOut,
    RequirementOut,
    ResultsOut,
    SummaryOut,
)
from app.services.github.client import parse_github_url
from app.services.jobs.fetch import JobFetchError, fetch_public_page
from app.services.jobs.parse import JobParseError, extract_job_from_html
from app.services.resume.extract import ResumeError, extract_resume, has_pdf_signature
from app.workers.pipeline import upload_path

router = APIRouter(prefix="/api/v1")
_hits: dict[str, deque] = defaultdict(deque)
MAX_JOB_TEXT = 30_000


def _rate_limit(request: Request) -> None:
    limit = request.app.state.settings.rate_limit_per_minute
    if limit <= 0:
        return
    ip = request.client.host if request.client else "unknown"
    q, now = _hits[ip], time.monotonic()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise AppError(429, "rate_limited", "Too many analyses started. Please wait a minute.")
    q.append(now)


def _fields(**errs: str) -> AppError:
    return AppError(422, "validation_error", "Request validation failed.",
                    {"fields": [{"field": k, "message": v} for k, v in errs.items()]})


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:  # noqa: BLE001
        raise AppError(503, "database_unavailable", "The database is not reachable.") from None


@router.get("/health/ai")
def health_ai(request: Request):
    st, deps = request.app.state.settings, request.app.state.deps
    out = {"llm_enabled": st.llm_enabled, "configured_model": st.ollama_model, "reachable": False,
           "model_installed": False, "installed_models": [], "detail": None,
           "embedding_backend": st.embedding_backend, "require_llm": st.require_llm}
    if deps.llm is not None:
        ok, reason, models = deps.llm.check()
        out.update(reachable=bool(models) or ok, model_installed=ok, installed_models=models, detail=reason)
    return out


@router.post("/analyses", status_code=202, response_model=AnalysisAccepted)
def create_analysis(
    request: Request,
    resume: UploadFile = File(...),
    job_mode: str = Form(...),
    job_description: str | None = Form(None),
    job_url: str | None = Form(None),
    manual_title: str | None = Form(None),
    manual_company: str | None = Form(None),
    manual_requirements: str | None = Form(None),
    github_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    st = request.app.state.settings
    _rate_limit(request)
    if job_mode not in ("paste", "url", "manual"):
        raise AppError(400, "invalid_job_mode", "job_mode must be one of: paste, url, manual.")

    # --- resume upload: size, signature, structure
    limit = st.max_upload_mb * 1024 * 1024
    data = bytearray()
    while chunk := resume.file.read(64 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise AppError(413, "file_too_large", f"The PDF exceeds the {st.max_upload_mb} MB limit.")
    if not data:
        raise AppError(422, "pdf_empty", "The uploaded file is empty.")
    if not has_pdf_signature(bytes(data[:1024])):
        raise AppError(415, "unsupported_file_type", "Only PDF files are supported.")
    try:
        doc = extract_resume(bytes(data), st.max_pdf_pages, st.min_resume_chars)
    except ResumeError as exc:
        raise AppError(422, exc.code, exc.message) from exc

    # --- job description
    title = company = source_url = None
    if job_mode == "paste":
        body = (job_description or "").strip()
        if len(body) < 50:
            raise _fields(job_description="Paste the job description (at least 50 characters).")
        job_text = body[:MAX_JOB_TEXT]
    elif job_mode == "manual":
        title = (manual_title or "").strip()
        reqs = (manual_requirements or "").strip()
        errs = {}
        if not title:
            errs["manual_title"] = "A job title is required."
        if not reqs:
            errs["manual_requirements"] = "Enter at least one requirement (one per line)."
        if errs:
            raise _fields(**errs)
        company = (manual_company or "").strip() or None
        job_text = reqs[:MAX_JOB_TEXT]
    else:
        if not (job_url or "").strip():
            raise _fields(job_url="A job URL is required.")
        try:
            page = fetch_public_page(job_url.strip(), st, resolver=request.app.state.resolver,
                                     transport=request.app.state.http_transport)
            title, company, job_text = extract_job_from_html(page.body)
        except (JobFetchError, JobParseError) as exc:
            raise AppError(502, "job_page_unavailable", str(exc)) from exc
        source_url = page.final_url

    # --- optional GitHub URL (syntax only here; retrieval happens in the worker)
    gh = (github_url or "").strip() or None
    if gh:
        try:
            parse_github_url(gh)
        except ValueError as exc:
            raise _fields(github_url=str(exc)) from exc

    if st.require_llm:
        ok = request.app.state.deps.llm is not None and request.app.state.deps.llm.check()[0]
        if not ok:
            raise AppError(503, "ai_unavailable", "The local AI service (Ollama/model) is unavailable.")

    analysis = Analysis(id=new_id(), resume_filename=(resume.filename or "resume.pdf")[:255],
                        resume_page_count=doc.page_count, github_url=gh, warnings=[])
    analysis.job = JobDescription(mode=job_mode, title=title, company=company,
                                  source_url=source_url, text=job_text)
    path = upload_path(st, analysis.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(data))
    try:
        db.add(analysis)
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    base = f"/api/v1/analyses/{analysis.id}"
    return AnalysisAccepted(id=analysis.id, status=analysis.status, created_at=analysis.created_at,
                            status_url=base, results_url=f"{base}/results")


def _get(db: Session, analysis_id: str) -> Analysis:
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise AppError(404, "analysis_not_found", "Analysis not found (it may have been deleted).")
    return a


@router.get("/analyses/{analysis_id}", response_model=AnalysisStatus)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    return _get(db, analysis_id)


@router.get("/analyses/{analysis_id}/results", response_model=ResultsOut)
def get_results(analysis_id: str, db: Session = Depends(get_db)):
    a = _get(db, analysis_id)
    if a.status == "failed":
        raise AppError(409, "analysis_failed", a.error_message or "The analysis failed.",
                       {"error_code": a.error_code})
    if a.status != "completed":
        raise AppError(409, "results_not_ready", "Results are not ready yet.",
                       {"status": a.status, "stage": a.stage, "progress": a.progress})
    reqs = db.scalars(select(JobRequirement).where(JobRequirement.analysis_id == a.id)
                      .order_by(JobRequirement.ordinal)).all()
    assessments = {x.requirement_id: x for x in db.scalars(
        select(RequirementAssessment).where(RequirementAssessment.analysis_id == a.id))}
    links: dict[str, list] = {}
    rows = db.execute(select(AssessmentEvidence, EvidenceItem).join(
        EvidenceItem, EvidenceItem.id == AssessmentEvidence.evidence_id).join(
        RequirementAssessment, RequirementAssessment.id == AssessmentEvidence.assessment_id).where(
        RequirementAssessment.analysis_id == a.id).order_by(AssessmentEvidence.rank)).all()
    for link, ev in rows:
        links.setdefault(link.assessment_id, []).append(EvidenceOut(
            id=ev.id, ref=ev.ref, source_type=ev.source_type, text=ev.text, quote=link.quote,
            page_number=ev.page_number, repo=ev.repo, source_url=ev.source_url, path=ev.path,
            line_start=ev.line_start, line_end=ev.line_end, commit_sha=ev.commit_sha,
            retrieved_at=ev.retrieved_at))
    out_reqs = []
    for r in reqs:
        x = assessments[r.id]
        out_reqs.append(RequirementOut(
            id=r.id, ordinal=r.ordinal, text=r.text, category=r.category, key_terms=r.key_terms,
            assessment=AssessmentOut(id=x.id, status=x.status, explanation=x.explanation, method=x.method,
                                     warnings=x.warnings, dismissed=x.dismissed,
                                     evidence=links.get(x.id, []))))
    active = [r for r in out_reqs if not r.assessment.dismissed]
    counts = {s: sum(r.assessment.status == s for r in active) for s in EVIDENCE_STATUSES}
    n = len(active)
    covered = counts["supported"] + counts["needs_better_evidence"] + counts["related_skill_found"]
    summary = SummaryOut(
        total_requirements=len(out_reqs), dismissed=len(out_reqs) - n, counts=counts,
        direct_support_share=round(counts["supported"] / n, 3) if n else None,
        evidence_coverage_share=round(covered / n, 3) if n else None,
        definitions={
            "direct_support_share": "Requirements with status 'supported' divided by non-dismissed requirements.",
            "evidence_coverage_share": "Requirements with at least one retrieved evidence item "
                                       "(supported, needs_better_evidence, related_skill_found) divided "
                                       "by non-dismissed requirements.",
        },
        disclaimer="These are descriptive evidence-coverage figures, not an ATS score or a prediction "
                   "of interview or hiring outcomes. Missing evidence is not proof of missing ability.")
    job = a.job
    return ResultsOut(
        analysis=AnalysisStatus.model_validate(a),
        job=JobOut(mode=job.mode, title=job.title, company=job.company, source_url=job.source_url),
        summary=summary, requirements=out_reqs,
        recommendations=[RecommendationOut(id=x.id, requirement_id=x.requirement_id, kind=x.kind, text=x.text)
                         for x in db.scalars(select(Recommendation).where(Recommendation.analysis_id == a.id)
                                             .order_by(Recommendation.priority))],
        interview_questions=[QuestionOut(id=x.id, requirement_id=x.requirement_id, question=x.question,
                                         rationale=x.rationale, source=x.source)
                             for x in db.scalars(select(InterviewQuestion).where(
                                 InterviewQuestion.analysis_id == a.id))])


@router.patch("/analyses/{analysis_id}/assessments/{assessment_id}")
def dismiss_assessment(analysis_id: str, assessment_id: str, body: DismissIn, db: Session = Depends(get_db)):
    _get(db, analysis_id)
    x = db.get(RequirementAssessment, assessment_id)
    if x is None or x.analysis_id != analysis_id:
        raise AppError(404, "assessment_not_found", "Finding not found.")
    x.dismissed = body.dismissed
    db.commit()
    return {"id": x.id, "dismissed": x.dismissed}


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, request: Request, db: Session = Depends(get_db)):
    """Idempotent: 204 whether or not it existed. Cascades to all child rows; the temp PDF is removed.
    A worker mid-run detects the deletion at its next checkpoint and stops without recreating anything."""
    a = db.get(Analysis, analysis_id)
    if a is not None:
        db.delete(a)
        db.commit()
    upload_path(request.app.state.settings, analysis_id).unlink(missing_ok=True)
    return Response(status_code=204)
