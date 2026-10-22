# System pipeline

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as API (sync validation)
  participant D as PostgreSQL
  participant W as Worker
  participant O as Ollama
  U->>A: POST /analyses (PDF + job + optional GitHub URL)
  A->>A: size, %PDF signature, open with PyMuPDF, page/text checks
  A->>A: job: paste | SSRF-guarded fetch+parse | manual
  A->>D: insert analysis(queued) + job text; save temp PDF
  A-->>U: 202 {id, status_url, results_url}
  loop poll
    U->>A: GET /analyses/{id}
  end
  W->>D: claim queued -> processing
  W->>W: extract resume, chunk (page refs)
  W->>O: extract requirements (validated vs job text) [if LLM available]
  W->>W: optional GitHub retrieval (bounded)
  W->>W: rank chunks; rule assessment per requirement
  W->>O: assess with excerpts only [if LLM available]
  W->>W: validate ids/quotes; reconcile with rules
  W->>W: recommendations (templates), questions (LLM or templates)
  W->>D: persist all rows in ONE transaction; status=completed
  W->>W: delete temp PDF (always)
  U->>A: GET /analyses/{id}/results
```

## Stages and progress
`queued 0` → `extracting_resume 10` → `extracting_requirements 25` → `retrieving_github 40` (only with a GitHub URL) → `retrieving_evidence 50` → `assessing_requirements 55–85` → `generating_advice 90` → `finalizing 96` → `completed 100`. Failure sets `failed` with `error_code`/`error_message`.

## Key rules
- **Chunks** keep source metadata: resume = page + stable ref `R-p{page}-c{n}` (whitespace-normalized text of that passage); GitHub = repo, path, line range, commit SHA, retrieval time.
- **Rule layer** (`assess.py`): explicit skill-lexicon match in a non-list resume passage ⇒ `supported`; skills-list-only or repo-only ⇒ `needs_better_evidence`; adjacent skills (e.g. MySQL for PostgreSQL) ⇒ `related_skill_found`; nothing ⇒ `no_evidence_found`; requirements with no lexicon term can only become `uncertain` or `no_evidence_found`. Multi-skill requirements need all skills unless the text contains "or"/"/".
- **LLM layer**: sees only the requirement and ≤6 excerpts inside delimited tags; output schema enforced by Ollama `format`; then validated (`validate.py`). A `supported` claim the rules can't confirm is downgraded; "none found" vs rules finding text ⇒ `uncertain`.
- **Fallbacks**: LLM unavailable/invalid ⇒ rules result plus a warning; GitHub failure ⇒ warning; no requirements found ⇒ failed with `no_requirements`.
- **Cancellation**: every progress write is `UPDATE … WHERE id AND status='processing'`; zero rows ⇒ the analysis was deleted ⇒ worker stops. Final persistence checks existence and relies on FK constraints.

## Metrics
`direct_support_share` = supported ÷ non-dismissed requirements. `evidence_coverage_share` = (supported + needs_better_evidence + related_skill_found) ÷ non-dismissed. Neither is an ATS score or a prediction.
