# MatchLens

A privacy-conscious resume-to-job match analyzer. Upload a resume PDF, add a job description (paste, URL or manual) and optionally a public GitHub URL. MatchLens extracts the job's requirements, finds supporting evidence in your resume (and permitted public repo files), and shows each requirement with an honest status, the exact source passage, truthful recommendations and interview questions.

**Principles:** "no evidence found" never means "you lack the skill"; nothing is invented (quotes are verified against sources); no hiring probabilities or ATS scores; inference is local (Ollama); the uploaded PDF is deleted after processing.

**Statuses:** `supported` · `needs_better_evidence` · `related_skill_found` · `no_evidence_found` · `uncertain`.

## Quick start
See **[RUN_STEPS.md](RUN_STEPS.md)** (same as `docs/setup-windows.md`) for the full PowerShell walkthrough. In short: PostgreSQL → `backend` (venv, `pip install -e ".[dev]"`, `alembic upgrade head`, `uvicorn app.main:app_factory --factory`) → Ollama model → `frontend` (`npm install`, `npm run dev`) → http://127.0.0.1:5173.

## Layout
`backend/` FastAPI + worker + Alembic · `frontend/` React/TS/Vite · `database/` role script · `model-tests/` local model checks · `tests/evaluation/` rule regression set · `docs/` documentation (start at `docs/README.md`).

## Status
Verified and running on Windows with local PostgreSQL, FastAPI backend, React/Vite frontend, and real local Ollama inference (`qwen2.5:3b`). The full end-to-end pipeline (PDF resume upload, structured requirement extraction, evidence matching, and interactive results dashboard) has been demonstrated live. See `docs/implementation-status.md` for detailed verification records and `docs/limitations-and-future-work.md`.
