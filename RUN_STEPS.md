# MatchLens — steps to run the application (Windows / PowerShell)

Everything runs locally: PostgreSQL, the FastAPI backend (with its background worker), Ollama, and the React frontend.
Use **four terminals** (database may be a service/container, so often three). Commands are for PowerShell.

> **Verification note.** This project has been executed and verified live on Windows (PowerShell, PostgreSQL 16, FastAPI backend, React/Vite frontend, and local Ollama inference with `qwen2.5:3b`). See `docs/implementation-status.md` for exact test and environment details.

## 0. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 preferred (3.12/3.13 should work; 3.14 untested — avoid) | `py -0p` |
| Node.js | 20 or newer | `node --version` |
| PostgreSQL | 16 (native install **or** Docker Desktop) | `psql --version` / `docker --version` |
| Ollama | current | `ollama list` |

If PowerShell blocks venv activation: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (affects only this window).

Unzip the project, then in every terminal start from the project root, e.g. `cd C:\path\to\MatchLens`.
Your existing `model-tests\.venv` is left alone; the backend uses its **own** venv in `backend\.venv`.

## 1. Database (pick A or B)

### A. Docker Desktop (not executed during development)
```powershell
copy .env.example .env          # then edit the three CHANGE_ME_* passwords
docker compose up -d db
docker compose ps               # wait until "healthy"
```
This creates the `matchlens` database and the roles `matchlens_owner` (migrations) and `matchlens_app` (runtime, no DDL).

### B. Native PostgreSQL 16
Create the database and roles once, as the `postgres` superuser (you will be prompted for its password):
```powershell
psql -U postgres -c "CREATE DATABASE matchlens;"
psql -U postgres -d matchlens `
  -v owner_password="'CHOOSE_OWNER_PASSWORD'" -v app_password="'CHOOSE_APP_PASSWORD'" `
  -f database\init\01-roles.sql
```
(The single quotes inside the double quotes are required.)

## 2. Backend (Terminal 1)
```powershell
cd backend
py -3.11 -m venv .venv                 # use `py -3.12` if 3.11 is not installed
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env
notepad .env                           # set the two passwords chosen in step 1; set OLLAMA_MODEL (step 3)
alembic upgrade head                   # creates tables (uses MIGRATION_DATABASE_URL, the owner role)
uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8000
```
Check: open http://127.0.0.1:8000/api/v1/health → `{"status":"ok","database":"ok"}`. Interactive API docs: http://127.0.0.1:8000/docs.

## 3. Ollama (Terminal 2 — only if not already running as the Windows tray app)
```powershell
ollama list                            # shows what you actually have installed
ollama serve                           # skip if the tray app is running (port 11434 already in use is fine)
```
Choose a model and put its **exact name** in `backend\.env` as `OLLAMA_MODEL=` (restart the backend after editing):
- Already installed per your notes: `deepseek-r1:8b`, `gemma4:e4b` (confirm with `ollama list`).
- Planned baseline: `ollama pull qwen2.5:3b` (not confirmed installed; ~2 GB download).

Verify what the backend sees: http://127.0.0.1:8000/api/v1/health/ai (`model_installed` should be `true`).
**If Ollama or the model is missing the app still works** in rule-based mode and says so in the results; set `REQUIRE_LLM=true` to refuse analyses instead.
Reasoning models (e.g. deepseek-r1) are slower; `<think>` blocks are stripped but not disabled.

Optional: measure your models (writes `model-tests\test_results\`):
```powershell
cd model-tests
.\.venv\Scripts\Activate.ps1           # your existing environment
python test_ollama.py                  # or: python test_ollama.py gemma4:e4b
python test_embeddings.py              # downloads all-MiniLM-L6-v2 on first run
```

## 4. Frontend (Terminal 3)
```powershell
cd frontend
copy .env.example .env                 # VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm install
npm run dev
```
Open **http://127.0.0.1:5173**. (CORS only allows 127.0.0.1:5173 and localhost:5173 by default; change `CORS_ORIGINS` if you use another port.)

## 5. Use it
1. Upload a text-based resume PDF (≤ 5 MB, ≤ 30 pages).
2. Provide the job: paste text, a public job URL, or manual entry (one requirement per line).
3. Optionally add a public GitHub profile/repository URL.
4. Click **Analyze**, wait for the stages to finish, then expand findings to see source passages. Dismiss wrong findings; delete the analysis when done.

## 6. Tests and checks
```powershell
# Backend (offline; no Ollama/internet needed)
cd backend; .\.venv\Scripts\Activate.ps1
pytest                                   # 85 tests expected to pass
ruff check app tests
# Optional: PostgreSQL integration test (use the app-role URL of a MIGRATED database)
$env:TEST_DATABASE_URL = "postgresql+psycopg://matchlens_app:YOUR_APP_PASSWORD@127.0.0.1:5432/matchlens"
pytest -m integration

# Rule-layer regression set (backend venv active, from repo root)
cd ..; python tests\evaluation\run_eval.py

# Frontend
cd frontend; npm run typecheck; npm test; npm run build
```
> `pytest -m integration` creates and deletes real analysis rows in the target database. Use a development database.

## 7. Optional: sentence-transformers retrieval
```powershell
cd backend; .\.venv\Scripts\Activate.ps1
pip install -e ".[ml]"                 # large download (PyTorch)
# in backend\.env:  EMBEDDING_BACKEND=sentence-transformers
```
Not tested in development (no model download was possible). Calibrate `SentenceTransformerRanker.min_related` with `model-tests\test_embeddings.py` first.

## 8. Reset / cleanup (destructive — read first)
- **Delete one analysis:** use the button in the UI (or `DELETE /api/v1/analyses/{id}`).
- **Wipe all application tables** (destroys ALL stored analyses; irreversible):
  ```powershell
  cd backend; alembic downgrade base; alembic upgrade head
  ```
- **Remove the Docker database entirely** (destroys the volume): `docker compose down -v`
- Temporary uploads live in `backend\data\uploads` and are normally removed automatically.

## 9. Stopping
Ctrl+C in each terminal; `docker compose stop db` if you used Docker.

## Troubleshooting quick list
See `docs/troubleshooting.md`. Most common: wrong DB password in `.env` (health shows 503), `alembic` run before the roles exist, Ollama model name mismatch (`/health/ai`), CORS error when the frontend port differs from `CORS_ORIGINS`.
