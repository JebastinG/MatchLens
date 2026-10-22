import httpx
import pymupdf

from app.models import EVIDENCE_STATUSES
from app.workers.pipeline import Deps, recover_interrupted, upload_path
from tests.conftest import JOB_TEXT, make_pdf, run_and_get, submit


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["database"] == "ok"
    ai = client.get("/api/v1/health/ai").json()
    assert ai["llm_enabled"] is False and ai["reachable"] is False


def test_full_paste_flow_results_are_traceable(client, settings):
    aid, res = run_and_get(client, submit(client))
    assert res.status_code == 200
    body = res.json()
    assert body["analysis"]["status"] == "completed" and body["analysis"]["analysis_mode"] == "deterministic"
    by_text = {r["text"]: r for r in body["requirements"]}
    py = by_text["3+ years of experience with Python"]["assessment"]
    assert py["status"] == "supported" and py["confidence"] is None
    for ev in py["evidence"]:
        assert ev["source_type"] == "resume" and ev["page_number"] == 1 and ev["ref"].startswith("R-p1")
    assert by_text["Experience with Kubernetes"]["assessment"]["status"] in ("related_skill_found", "no_evidence_found")
    s = body["summary"]
    assert set(s["counts"]) == set(EVIDENCE_STATUSES) and sum(s["counts"].values()) == s["total_requirements"]
    assert "not an ATS score" in s["disclaimer"]
    assert body["recommendations"] and body["interview_questions"]
    assert not upload_path(settings, aid).exists()  # temp PDF removed after processing


def test_every_displayed_quotation_is_a_substring_of_extracted_text(client):
    _, res = run_and_get(client, submit(client))
    resume_text = " ".join(" ".join(p.split()) for p in [
        pymupdf.open(stream=make_pdf(), filetype="pdf")[0].get_text()])
    for r in res.json()["requirements"]:
        for ev in r["assessment"]["evidence"]:
            assert " ".join(ev["text"].split()) in resume_text


def test_results_409_until_complete_then_status(client):
    aid = submit(client).json()["id"]
    r = client.get(f"/api/v1/analyses/{aid}/results")
    assert r.status_code == 409 and r.json()["error"]["code"] == "results_not_ready"
    assert client.get(f"/api/v1/analyses/{aid}").json()["status"] == "queued"


def test_manual_mode_and_validation(client):
    r = submit(client, job_mode="manual", manual_title="Dev", manual_requirements="- Python\n- Terraform",
               job_description=None)
    _, res = run_and_get(client, r)
    st = {x["text"]: x["assessment"]["status"] for x in res.json()["requirements"]}
    assert st["Python"] == "supported" and st["Terraform"] == "no_evidence_found"
    bad = submit(client, job_mode="manual", job_description=None)
    assert bad.status_code == 422 and len(bad.json()["error"]["details"]["fields"]) == 2


def test_input_errors(client, settings):
    assert submit(client, job_mode="bogus").status_code == 400
    assert submit(client, job_description="short").status_code == 422
    assert submit(client, pdf=b"MZ not a pdf at all").status_code == 415
    assert submit(client, pdf=b"").status_code == 422
    assert submit(client, pdf=b"%PDF-1.4 garbage").json()["error"]["code"] == "pdf_corrupt"
    assert submit(client, github_url="https://evil.com/x/y").status_code == 422
    settings.max_upload_mb = 0
    assert submit(client).status_code == 413


def test_encrypted_text_poor_and_too_many_pages(client, settings, tmp_path):
    d = pymupdf.open(stream=make_pdf(), filetype="pdf")
    enc = d.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="o", user_pw="u")
    assert submit(client, pdf=enc).json()["error"]["code"] == "pdf_encrypted"
    blank = pymupdf.open()
    blank.new_page()
    assert submit(client, pdf=blank.tobytes()).json()["error"]["code"] == "pdf_no_text"
    settings.max_pdf_pages = 1
    assert submit(client, pdf=make_pdf(pages=2)).json()["error"]["code"] == "pdf_too_many_pages"


def test_url_mode_uses_safe_fetch(make_client, settings):
    html = "<html><body><h1>Backend Dev</h1><ul>" + "".join(
        f"<li>Experience with Python and tool {i}</li>" for i in range(12)) + "</ul></body></html>"
    seen = {}

    def handler(req):
        seen["host"] = req.headers["host"]
        return httpx.Response(200, headers={"content-type": "text/html"}, text=html)
    c = make_client(resolver=lambda h, p: ["93.184.216.34"], http_transport=httpx.MockTransport(handler))
    r = submit(c, job_mode="url", job_url="https://jobs.example.test/1", job_description=None)
    _, res = run_and_get(c, r)
    assert res.json()["job"]["title"] == "Backend Dev" and seen["host"] == "jobs.example.test"


def test_dismiss_and_summary_recomputed(client):
    aid, res = run_and_get(client, submit(client))
    body = res.json()
    a = body["requirements"][0]["assessment"]
    assert client.patch(f"/api/v1/analyses/{aid}/assessments/{a['id']}", json={"dismissed": True}).status_code == 200
    s2 = client.get(f"/api/v1/analyses/{aid}/results").json()["summary"]
    assert s2["dismissed"] == 1 and s2["total_requirements"] == body["summary"]["total_requirements"]
    assert client.patch(f"/api/v1/analyses/{aid}/assessments/nope", json={"dismissed": True}).status_code == 404


def test_delete_is_idempotent_cascades_and_removes_pdf(client, settings):
    aid = submit(client).json()["id"]
    assert upload_path(settings, aid).exists()
    assert client.delete(f"/api/v1/analyses/{aid}").status_code == 204
    assert client.delete(f"/api/v1/analyses/{aid}").status_code == 204
    assert client.get(f"/api/v1/analyses/{aid}").status_code == 404
    assert not upload_path(settings, aid).exists()
    assert client.app.state.worker.process_one() is False

    aid2, _ = run_and_get(client, submit(client))
    assert client.delete(f"/api/v1/analyses/{aid2}").status_code == 204
    from app.db.session import session_scope
    from app.models import EvidenceItem, JobRequirement, RequirementAssessment
    with session_scope() as s:
        for m in (EvidenceItem, JobRequirement, RequirementAssessment):
            assert s.query(m).filter_by(analysis_id=aid2).count() == 0


def test_delete_during_processing_does_not_recreate_rows(make_client, settings):
    holder = {}

    def gh(url):  # runs inside the worker; user deletes mid-run
        holder["client"].delete(f"/api/v1/analyses/{holder['aid']}")
        return [], []
    c = make_client(Deps(settings, github_fetch=gh))
    holder["client"] = c
    r = submit(c, github_url="https://github.com/o/r")
    holder["aid"] = r.json()["id"]
    assert c.app.state.worker.process_one() is True
    assert c.get(f"/api/v1/analyses/{holder['aid']}").status_code == 404
    from app.db.session import session_scope
    from app.models import JobRequirement
    with session_scope() as s:
        assert s.query(JobRequirement).count() == 0


def test_github_failure_is_warning_only(make_client, settings):
    c = make_client(Deps(settings, github_fetch=lambda u: ([], ["not found (or it is private)."])))
    _, res = run_and_get(c, submit(c, github_url="https://github.com/o/r"))
    assert res.status_code == 200 and any("GitHub:" in w for w in res.json()["analysis"]["warnings"])


def test_pipeline_failure_marks_failed_and_cleans_up(make_client, settings):
    def boom(url):
        raise RuntimeError("secret internal detail")
    c = make_client(Deps(settings, github_fetch=boom))
    aid, res = run_and_get(c, submit(c, github_url="https://github.com/o/r"))
    assert res.status_code == 409 and res.json()["error"]["code"] == "analysis_failed"
    st = c.get(f"/api/v1/analyses/{aid}").json()
    assert st["status"] == "failed" and "secret" not in str(st)
    assert not upload_path(settings, aid).exists()


def test_recovery_requeues_then_fails_after_max_attempts(client, settings):
    from app.db.session import session_scope
    from app.models import Analysis
    aid = submit(client).json()["id"]
    assert client.app.state.worker.process_one() is True  # completes
    aid2 = submit(client).json()["id"]
    with session_scope() as s:
        a = s.get(Analysis, aid2)
        a.status, a.attempts = "processing", 1
    assert recover_interrupted(settings) == 1
    assert client.get(f"/api/v1/analyses/{aid2}").json()["status"] == "queued"
    with session_scope() as s:
        a = s.get(Analysis, aid2)
        a.status, a.attempts = "processing", settings.worker_max_attempts
    assert recover_interrupted(settings) == 0
    st = client.get(f"/api/v1/analyses/{aid2}").json()
    assert st["status"] == "failed" and st["error_code"] == "worker_interrupted"
    assert not upload_path(settings, aid2).exists() and aid


def test_require_llm_returns_503_when_unavailable(make_client, settings):
    settings.require_llm = True
    c = make_client()
    r = submit(c)
    assert r.status_code == 503 and r.json()["error"]["code"] == "ai_unavailable"


_ = JOB_TEXT
