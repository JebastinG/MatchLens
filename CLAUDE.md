# MatchLens — working notes for Claude Code

Privacy-first resume-to-job match analyzer. Modular monolith: React/TS/Vite frontend, FastAPI backend, PostgreSQL, local Ollama.

## Invariants (do not break)
1. Evidence status is exactly one of: supported, needs_better_evidence, related_skill_found, no_evidence_found, uncertain. "No evidence" never means "lacks the skill".
2. Never fabricate quotes, paths, scores or probabilities. LLM output is untrusted: statuses, evidence ids and quotes are validated in `app/services/evidence/validate.py`; rules can only cap, never be raised by, the model.
3. No external LLM providers. Inference is local (Ollama). Browser never talks to Ollama.
4. Job URLs go through `app/utils/ssrf.py` + `services/jobs/fetch.py` (validate every hop, pin IP, size/time limits). Do not add other outbound fetches.
5. The uploaded PDF is deleted after processing (`workers/pipeline.py`). Never log resume/job/repo text.
6. Worker is a single DB-backed thread; deleting an analysis must stop it without recreating rows.
7. Migrations via Alembic only; the app DB role has no DDL rights.

## Commands (PowerShell, from repo root)
- Backend tests: `cd backend; .\.venv\Scripts\Activate.ps1; pytest` (integration: `pytest -m integration` with `TEST_DATABASE_URL`)
- Lint: `ruff check app tests`
- Migrate: `alembic upgrade head`  | Run API: `uvicorn app.main:app_factory --factory --port 8000`
- Frontend: `cd frontend; npm run typecheck; npm run build; npm test; npm run dev`
- Rule-layer regression: `python tests/evaluation/run_eval.py`

## Conventions
Keep deps minimal. Update `docs/implementation-status.md` when finishing work. Docs describe what exists, not what is planned. Do not touch `model-tests/.venv`.
