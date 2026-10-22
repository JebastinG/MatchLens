"""Analysis pipeline. Runs in the background worker; every stage checks the analysis still exists."""
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.session import session_factory, session_scope
from app.models import (
    Analysis,
    AssessmentEvidence,
    EvidenceItem,
    InterviewQuestion,
    JobRequirement,
    Recommendation,
    RequirementAssessment,
)
from app.services.embeddings.embedder import Ranker, make_ranker
from app.services.evidence.advice import ReqView, build_questions, build_recommendations
from app.services.evidence.assess import Assessment, Scored, assess_rules, score_chunks
from app.services.evidence.chunking import EvidenceChunk, chunk_resume
from app.services.evidence.validate import reconcile, validate_llm_assessment
from app.services.github.client import fetch_github_evidence
from app.services.jobs.requirements import (
    Req,
    extract_requirements_heuristic,
    requirements_from_manual,
    validate_llm_requirements,
)
from app.services.llm import tasks as T
from app.services.llm.ollama import LLMUnavailable, OllamaClient
from app.services.resume.extract import ResumeError, extract_resume

log = logging.getLogger("matchlens.pipeline")


class Cancelled(Exception):
    """Analysis was deleted while processing."""


@dataclass
class Deps:
    settings: Settings
    llm: OllamaClient | None = None
    ranker_factory: Callable[[], tuple[Ranker, str | None]] | None = None
    github_fetch: Callable[[str], tuple[list[EvidenceChunk], list[str]]] | None = None


def default_deps(settings: Settings) -> Deps:
    llm = None
    if settings.llm_enabled:
        llm = OllamaClient(settings.ollama_base_url, settings.ollama_model,
                           settings.ollama_timeout_s, settings.ollama_num_ctx)
    return Deps(
        settings, llm,
        lambda: make_ranker(settings.embedding_backend, settings.embedding_model),
        lambda url: fetch_github_evidence(url, settings),
    )


def upload_path(settings: Settings, analysis_id: str) -> Path:
    return settings.upload_dir / f"{analysis_id}.pdf"


def _progress(analysis_id: str, stage: str, pct: int) -> None:
    with session_scope() as s:
        res = s.execute(update(Analysis).where(Analysis.id == analysis_id, Analysis.status == "processing")
                        .values(stage=stage, progress=pct, updated_at=datetime.now(UTC)))
        if res.rowcount == 0:
            raise Cancelled()


def _fail(analysis_id: str, code: str, message: str) -> None:
    with session_scope() as s:
        s.execute(update(Analysis).where(Analysis.id == analysis_id).values(
            status="failed", stage="failed", error_code=code, error_message=message,
            completed_at=datetime.now(UTC)))


def _candidates(terms: list[str], scored: list[Scored], k: int = 4) -> list[Scored]:
    explicit = [s for s in scored if set(terms) & set(s.terms)][:3]
    top = sorted(scored, key=lambda s: -s.score)[:k]
    seen, out = set(), []
    for s in explicit + [t for t in top if t.score > 0]:
        if s.chunk.ref not in seen:
            seen.add(s.chunk.ref)
            out.append(s)
    return out[:6]


def run_analysis(analysis_id: str, deps: Deps) -> None:
    st = deps.settings
    try:
        _run(analysis_id, deps)
    except Cancelled:
        log.info("analysis %s was deleted during processing", analysis_id)
    except ResumeError as exc:
        _fail(analysis_id, exc.code, exc.message)
    except Exception:  # noqa: BLE001 - never leak details or content
        log.exception("analysis %s failed", analysis_id)
        _fail(analysis_id, "pipeline_error", "The analysis failed unexpectedly. Please try again.")
    finally:
        upload_path(st, analysis_id).unlink(missing_ok=True)  # retention: PDF is never kept


def _run(analysis_id: str, deps: Deps) -> None:
    st = deps.settings
    warnings: list[str] = []
    with session_scope() as s:
        a = s.get(Analysis, analysis_id)
        if a is None:
            raise Cancelled()
        job = a.job
        job_mode, job_text, github_url = job.mode, job.text, a.github_url

    # 1. resume
    _progress(analysis_id, "extracting_resume", 10)
    path = upload_path(st, analysis_id)
    if not path.exists():
        raise ResumeError("upload_missing", "The uploaded file is no longer available. Please resubmit.")
    doc = extract_resume(str(path), st.max_pdf_pages, st.min_resume_chars)
    chunks = chunk_resume(doc.pages)

    # LLM availability (never required unless REQUIRE_LLM, which is enforced at submission)
    llm = deps.llm
    llm_used = False
    if llm is not None:
        ok, reason, _ = llm.check()
        if not ok:
            warnings.append(f"Local LLM unavailable ({reason}) Rule-based analysis was used.")
            llm = None

    # 2. requirements
    _progress(analysis_id, "extracting_requirements", 25)
    reqs: list[Req] = []
    if job_mode == "manual":
        reqs = requirements_from_manual(job_text, st.max_requirements)
    else:
        if llm is not None:
            try:
                raw = llm.chat_json(T.REQ_SYSTEM, T.requirements_prompt(job_text, st.max_requirements),
                                    T.REQ_SCHEMA, num_predict=900)
                reqs, dropped = validate_llm_requirements(raw, job_text, st.max_requirements)
                llm_used = llm_used or bool(reqs)
                if dropped:
                    warnings.append(f"{dropped} model-proposed requirement(s) were discarded because "
                                    "they were not grounded in the job text.")
            except LLMUnavailable:
                warnings.append("The local model failed during requirement extraction; rules were used.")
                llm = None
        if not reqs:
            reqs = extract_requirements_heuristic(job_text, st.max_requirements)
    if not reqs:
        raise ResumeError("no_requirements",
                          "No job requirements could be identified. Add requirements via Manual Entry.")

    # 3. github
    gh_chunks: list[EvidenceChunk] = []
    if github_url and deps.github_fetch:
        _progress(analysis_id, "retrieving_github", 40)
        gh_chunks, gh_warn = deps.github_fetch(github_url)
        warnings += [f"GitHub: {w}" for w in gh_warn]
    all_chunks = chunks + gh_chunks

    # 4. retrieval + assessment
    _progress(analysis_id, "retrieving_evidence", 50)
    ranker, ranker_warn = (deps.ranker_factory() if deps.ranker_factory else make_ranker("lexical", ""))
    if ranker_warn:
        warnings.append(ranker_warn)
    ranker.fit([c.text for c in all_chunks])

    results: list[Assessment] = []
    llm_budget = st.llm_max_requirements
    for i, rq in enumerate(reqs):
        _progress(analysis_id, "assessing_requirements", 55 + int(30 * i / len(reqs)))
        scored = score_chunks(all_chunks, ranker.score(rq.text))
        det = assess_rules(rq.text, rq.key_terms or [], scored, ranker.min_related)
        final = det
        if llm is not None and i < llm_budget:
            cands = _candidates(rq.key_terms or [], scored)
            allowed = {c.chunk.ref: c.chunk for c in cands}
            llm_res = None
            if allowed:
                try:
                    for _attempt in range(2):
                        raw = llm.chat_json(T.ASSESS_SYSTEM, T.assessment_prompt(rq.text, [c.chunk for c in cands]),
                                            T.ASSESS_SCHEMA)
                        llm_res = validate_llm_assessment(raw, allowed)
                        if llm_res:
                            break
                    if llm_res is None:
                        det.warnings.append("The model's answer was invalid; rule-based result shown.")
                    else:
                        llm_used = True
                        final = reconcile(det, llm_res)
                except LLMUnavailable:
                    warnings.append("The local model became unavailable; remaining requirements used rules.")
                    llm = None
        results.append(final)
    if len(reqs) > llm_budget and llm_used:
        warnings.append(f"Model assessment was limited to the first {llm_budget} requirements.")

    # 5. advice
    _progress(analysis_id, "generating_advice", 90)
    views = [ReqView(i + 1, rq.text, rq.category, r.status, rq.key_terms or [],
                     r.evidence[0][1] or r.evidence[0][0].text if r.evidence else None)
             for i, (rq, r) in enumerate(zip(reqs, results, strict=True))]
    recs = build_recommendations(views)
    qs = [(o, q, why, "template") for o, q, why in build_questions(views)]
    if llm is not None and views:
        qs = _llm_questions(llm, views, qs)

    # 6. persist atomically
    _progress(analysis_id, "finalizing", 96)
    _persist(analysis_id, reqs, results, recs, qs, warnings, llm_used, deps, ranker.name, ranker_warn)


def _llm_questions(llm: OllamaClient, views: list[ReqView], fallback):
    items = [(f"REQ-{v.ordinal}", v.text, v.status, v.quote) for v in views[:15]]
    try:
        raw = llm.chat_json(T.Q_SYSTEM, T.questions_prompt(items, 8), T.Q_SCHEMA, num_predict=900)
    except LLMUnavailable:
        return fallback
    valid = {f"REQ-{v.ordinal}": v.ordinal for v in views}
    out = []
    for q in (raw.get("questions") if isinstance(raw, dict) else None) or []:
        if (isinstance(q, dict) and q.get("requirement_id") in valid
                and isinstance(q.get("question"), str) and isinstance(q.get("rationale"), str)
                and 10 <= len(q["question"]) <= 400 and q["rationale"].strip()):
            out.append((valid[q["requirement_id"]], q["question"].strip(), q["rationale"].strip()[:300], "llm"))
    return out[:8] or fallback


def _persist(analysis_id, reqs, results, recs, qs, warnings, llm_used, deps, ranker_name, ranker_warn):
    st = deps.settings
    try:
        with session_scope() as s:
            a = s.get(Analysis, analysis_id)
            if a is None:
                raise Cancelled()
            req_rows: list[JobRequirement] = []
            for i, rq in enumerate(reqs, start=1):
                row = JobRequirement(analysis_id=analysis_id, ordinal=i, text=rq.text,
                                     category=rq.category, key_terms=rq.key_terms or [])
                s.add(row)
                req_rows.append(row)
            s.flush()
            ev_rows: dict[str, EvidenceItem] = {}
            for res in results:
                for chunk, _quote in res.evidence:
                    if chunk.ref not in ev_rows:
                        row = EvidenceItem(
                            analysis_id=analysis_id, ref=chunk.ref, source_type=chunk.source_type,
                            text=chunk.text, page_number=chunk.page, repo=chunk.repo,
                            source_url=chunk.source_url, path=chunk.path, line_start=chunk.line_start,
                            line_end=chunk.line_end, commit_sha=chunk.commit_sha,
                            retrieved_at=chunk.retrieved_at)
                        s.add(row)
                        ev_rows[chunk.ref] = row
            s.flush()
            for rq_row, res in zip(req_rows, results, strict=True):
                ar = RequirementAssessment(analysis_id=analysis_id, requirement_id=rq_row.id,
                                           status=res.status, explanation=res.explanation,
                                           method=res.method, warnings=res.warnings)
                s.add(ar)
                s.flush()
                for rank, (chunk, quote) in enumerate(res.evidence):
                    s.add(AssessmentEvidence(assessment_id=ar.id, evidence_id=ev_rows[chunk.ref].id,
                                             rank=rank, quote=quote))
            for ordinal, kind, text, pri in recs:
                s.add(Recommendation(analysis_id=analysis_id, requirement_id=req_rows[ordinal - 1].id,
                                     kind=kind, text=text, priority=pri))
            for ordinal, q, why, src in qs:
                s.add(InterviewQuestion(analysis_id=analysis_id, requirement_id=req_rows[ordinal - 1].id,
                                        question=q, rationale=why, source=src))
            a.status, a.stage, a.progress = "completed", "completed", 100
            a.completed_at = datetime.now(UTC)
            a.warnings = warnings
            a.analysis_mode = "llm" if llm_used else "deterministic"
            a.llm_model = st.ollama_model if llm_used else None
            a.embedding_backend = ranker_name
    except IntegrityError as exc:  # parent deleted between check and insert
        raise Cancelled() from exc


# ---- durable DB-backed queue ------------------------------------------------------------------

def claim_next() -> str | None:
    with session_scope() as s:
        aid = s.scalar(select(Analysis.id).where(Analysis.status == "queued")
                       .order_by(Analysis.created_at).limit(1))
        if aid is None:
            return None
        res = s.execute(update(Analysis).where(Analysis.id == aid, Analysis.status == "queued").values(
            status="processing", stage="starting", started_at=datetime.now(UTC),
            attempts=Analysis.attempts + 1))
        return aid if res.rowcount == 1 else None


def recover_interrupted(settings: Settings) -> int:
    """After a crash/restart: requeue 'processing' rows (bounded attempts), fail the rest."""
    n = 0
    with session_scope() as s:
        for a in s.scalars(select(Analysis).where(Analysis.status == "processing")):
            if a.attempts < settings.worker_max_attempts and upload_path(settings, a.id).exists():
                a.status, a.stage, a.progress = "queued", "queued", 0
                n += 1
            else:
                a.status, a.stage = "failed", "failed"
                a.error_code, a.error_message = "worker_interrupted", "Processing was interrupted. Please resubmit."
                a.completed_at = datetime.now(UTC)
    sweep_orphan_uploads(settings)
    return n


def sweep_orphan_uploads(settings: Settings) -> None:
    if not settings.upload_dir.exists():
        return
    with session_scope() as s:
        live = set(s.scalars(select(Analysis.id).where(Analysis.status.in_(("queued", "processing")))))
    for f in settings.upload_dir.glob("*.pdf"):
        if f.stem not in live:
            f.unlink(missing_ok=True)


class Worker:
    """Single background thread => at most one analysis (and one LLM call) at a time."""

    def __init__(self, deps: Deps):
        self.deps = deps
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def process_one(self) -> bool:
        aid = claim_next()
        if aid is None:
            return False
        run_analysis(aid, self.deps)
        return True

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if not self.process_one():
                    self._stop.wait(self.deps.settings.worker_poll_interval_s)
            except Exception:  # noqa: BLE001
                log.exception("worker loop error")
                self._stop.wait(2.0)

    def start(self) -> None:
        recover_interrupted(self.deps.settings)
        self._thread = threading.Thread(target=self._loop, name="matchlens-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)


_ = session_factory  # re-exported for tests
