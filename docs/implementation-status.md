# Implementation status

Last updated: 2026-10-22. Environments verified:
- **Windows (Active environment):** Tested and demonstrated live in PowerShell with native PostgreSQL 16 (dual-role security model: `matchlens_owner` for Alembic, `matchlens_app` for API), FastAPI backend + background worker, React 18 / Vite frontend, and local Ollama inference with `qwen2.5:3b`.
- **Linux sandbox:** Python 3.12.3, Node 22.22.2, PostgreSQL 16.2 (embedded via `pgserver`). 85 backend tests passed, clean build.

## Completed and verified (actual results)
| Item | Result |
|---|---|
| Windows live pipeline demonstration | Executed via PowerShell. Full workflow (resume PDF upload, requirement extraction with local Ollama `qwen2.5:3b`, lexical evidence matching, analysis storage in PG, frontend polling, and results dashboard) verified end-to-end. |
| Real Ollama inference (`qwen2.5:3b`) | Verified live against local Ollama instance (`http://127.0.0.1:11434`). Structured requirement extraction tested with real model outputs; tag stripping added and verified in backend and frontend. |
| Browser UI demonstration | React/Vite frontend verified in browser at `http://127.0.0.1:5173`; requirement cards, status badges, evidence passages, recommendations, and dismiss interactions working. |
| Backend tests (`pytest`) | 85 passed (unit, integration, security; SQLite temp DB, mocked HTTP, scripted fake LLM) |
| PostgreSQL integration test | 1 passed against PG 16.2 as the least-privilege app role |
| Clean-venv install (`pip install -e ".[dev]"`) then `pytest` | 85 passed |
| Ruff | clean (E501 line length and B008 ignored by config) |
| Alembic | `upgrade head` from empty DB, `check` (no drift), `downgrade base`, `upgrade head` — all OK on PG 16.2 |
| Live HTTP run (uvicorn + background worker + PG) | submit → poll → completed → results → delete (204) → 404; CORS preflight allowed `http://localhost:5173`; `169.254.169.254` job URL rejected with 502; temp upload removed |
| App role has no DDL | `CREATE TABLE` as `matchlens_app` rejected |
| Frontend build & tests | `tsc` clean; vitest 4 passed; `vite build` OK (≈179 kB JS, 13 kB CSS) |
| Rule-layer regression set | 10/10 (one label adjusted after seeing output — see AI doc) |
| Pinned dependency versions seen in sandbox | fastapi 0.156.8, uvicorn 0.54.0, pydantic 2.14.1, SQLAlchemy 2.1.5, alembic 1.20.0, psycopg 3.3.6, PyMuPDF 2.0, httpx 0.28.1, beautifulsoup4 4.15.0, pytest 9.1.1, ruff 0.17.1; react 18.3.1, vite 5.4.21, typescript 5.6.3, vitest 2.1.9, lucide-react 0.460.0. `pyproject.toml` uses lower bounds (`>=`), not exact pins. |

## Implemented but NOT verified
- Alternate Ollama models (`deepseek-r1:8b`, `gemma4:e4b`): only `qwen2.5:3b` has been run and verified live. Formal latency/RAM benchmarking tables not yet populated.
- sentence-transformers / MiniLM retrieval path (`EMBEDDING_BACKEND=sentence-transformers`).
- Real job-page fetching over live internet TLS with IP pinning; live GitHub API against external repos (mocked transport tested).
- Docker Compose database (`docker-compose.yml`, `database/init/docker-init.sh`) — native local PostgreSQL was used instead.
- Formal accessibility audit with assistive technology (screen readers).

## Not implemented
shadcn/ui + Radix + Tailwind (plain CSS used), MagicMouse.js, charts, OCR, Playwright, authentication, automatic data expiry, server-side retry, dependency vulnerability scans. Web research was limited to two searches (Ollama structured outputs, OWASP SSRF); other library behaviour was verified by running code, not by reading docs.

## Next actions
1. Benchmark additional models (`deepseek-r1:8b`, `gemma4:e4b`) and record metrics in `ai-models-and-evaluation.md`.
2. Try `EMBEDDING_BACKEND=sentence-transformers` with `all-MiniLM-L6-v2`.
3. Try live job URL extraction and public GitHub repository retrieval.
4. Run browser accessibility audit (axe, screen readers).
