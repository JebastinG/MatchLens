# API contract (v1)

Base: `http://127.0.0.1:8000/api/v1`. Interactive schema at `/docs`. Errors always: `{"error":{"code","message","details"}}`.

| Method & path | Success | Notes |
|---|---|---|
| `GET /health` | 200 `{status, database}` | 503 `database_unavailable` |
| `GET /health/ai` | 200 | configured model, reachability, installed models, embedding backend |
| `POST /analyses` | **202** `{id,status,created_at,status_url,results_url}` | multipart, below |
| `GET /analyses/{id}` | 200 status/stage/progress/warnings/error | 404 `analysis_not_found` |
| `GET /analyses/{id}/results` | 200 results | 409 `results_not_ready` (details: status/stage/progress) or `analysis_failed` |
| `PATCH /analyses/{id}/assessments/{assessment_id}` | 200 `{id,dismissed}` | body `{"dismissed":true}`; summary is recomputed on next read |
| `DELETE /analyses/{id}` | **204** always (idempotent) | cascades; removes temp PDF; running worker stops |

## POST /analyses (multipart/form-data)
`resume` (PDF, required) · `job_mode` = `paste|url|manual` · `job_description` (paste, ≥50 chars) · `job_url` (url) · `manual_title` + `manual_requirements` (manual; one requirement per line) · `manual_company` (optional) · `github_url` (optional).

| Status | Code(s) |
|---|---|
| 400 | `invalid_job_mode` |
| 413 | `file_too_large` |
| 415 | `unsupported_file_type` (no `%PDF-` signature) |
| 422 | `validation_error` (with `details.fields`), `pdf_empty`, `pdf_corrupt`, `pdf_encrypted`, `pdf_too_many_pages`, `pdf_no_text` (scanned/image PDFs; no OCR) |
| 429 | `rate_limited` (per-IP, default 10/min) |
| 502 | `job_page_unavailable` (blocked address, timeout, non-HTML, too large, no job text found) |
| 503 | `ai_unavailable` (only when `REQUIRE_LLM=true`) |

Example:
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/analyses -F "resume=@resume.pdf;type=application/pdf" -F job_mode=paste -F "job_description=<text>"
```

## Results shape (abridged)
```json
{
 "analysis": {"id":"…","status":"completed","analysis_mode":"deterministic|llm","warnings":["…"], "…":"…"},
 "job": {"mode":"paste","title":null,"company":null,"source_url":null},
 "summary": {"total_requirements":6,"dismissed":0,
   "counts":{"supported":2,"needs_better_evidence":0,"related_skill_found":1,"no_evidence_found":3,"uncertain":0},
   "direct_support_share":0.333,"evidence_coverage_share":0.5,"definitions":{"…":"…"},"disclaimer":"…"},
 "requirements": [{"id":"…","ordinal":1,"text":"…","category":"required","key_terms":["python"],
   "assessment":{"id":"…","status":"supported","explanation":"…","method":"deterministic|llm|reconciled",
     "confidence":null,"warnings":[],"dismissed":false,
     "evidence":[{"ref":"R-p1-c5","source_type":"resume","text":"…","quote":null,"page_number":1,
                  "repo":null,"source_url":null,"path":null,"line_start":null,"line_end":null,
                  "commit_sha":null,"retrieved_at":null}]}}],
 "recommendations":[{"id":"…","requirement_id":"…","kind":"clarify_evidence|add_evidence|learning_priority","text":"…"}],
 "interview_questions":[{"id":"…","requirement_id":"…","question":"…","rationale":"…","source":"template|llm"}]
}
```
`quote` is set only when the LLM supplied a quotation that was verified as a substring of `text`. GitHub evidence fills `repo/source_url/path/line_*/commit_sha/retrieved_at`.

Deviations from the original proposal: added `PATCH …/assessments/{id}` (dismiss) and `429`; `DELETE` is idempotent (204 even when missing); the job-URL fetch happens before acceptance, so `502` is returned synchronously and no analysis is created.
