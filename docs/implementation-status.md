# Implementation status

Last updated: 2026-10-22. Environment used for verification: Linux sandbox, Python 3.12.3, Node 22.22.2, PostgreSQL 16.2 (embedded via `pgserver`). **Not Windows. No Ollama. No Hugging Face/job-site/GitHub access.**

## Completed and verified (actual results)
| Item | Result |
|---|---|
| Backend tests (`pytest`) | 85 passed (unit, integration, security; SQLite temp DB, mocked HTTP, scripted fake LLM) |
| PostgreSQL integration test | 1 passed against PG 16.2 as the least-privilege app role |
| Clean-venv install (`pip install -e ".[dev]"`) then `pytest` | 85 passed |
| Ruff | clean (E501 line length and B008 ignored by config) |
| Alembic | `upgrade head` from empty DB, `check` (no drift), `downgrade base`, `upgrade head` — all OK on PG 16.2 |
| Live HTTP run (uvicorn + background worker + PG) | submit → poll → completed → results → delete (204) → 404; CORS preflight allowed `http://localhost:5173`; `169.254.169.254` job URL rejected with 502; temp upload removed |
| App role has no DDL | `CREATE TABLE` as `matchlens_app` rejected |
| Frontend | `tsc` clean; vitest 4 passed; `vite build` OK (≈179 kB JS, 13 kB CSS) |
| Rule-layer regression set | 10/10 (one label adjusted after seeing output — see AI doc) |
| Pinned dependency versions seen in sandbox | fastapi 0.156.8, uvicorn 0.54.0, pydantic 2.14.1, SQLAlchemy 2.1.5, alembic 1.20.0, psycopg 3.3.6, PyMuPDF 2.0, httpx 0.28.1, beautifulsoup4 4.15.0, pytest 9.1.1, ruff 0.17.1; react 18.3.1, vite 5.4.21, typescript 5.6.3, vitest 2.1.9, lucide-react 0.460.0. `pyproject.toml` uses lower bounds (`>=`), not exact pins. |

## Implemented but NOT verified
- Anything on Windows (PowerShell commands, `py -3.11`, paths). Code avoids 3.12-only syntax, but 3.11 was not run.
- Real Ollama calls (qwen2.5:3b / deepseek-r1:8b / gemma4:e4b): only mocked. No latency/memory numbers.
- sentence-transformers / MiniLM retrieval path.
- Real job-page fetching over TLS with IP pinning; real GitHub API (mocked transport only).
- Docker Compose database (`docker-compose.yml`, `database/init/docker-init.sh`).
- The UI in a browser (rendering, layout, accessibility with assistive tech). No screenshots were taken.

## Not implemented
shadcn/ui + Radix + Tailwind (plain CSS used), MagicMouse.js, charts, OCR, Playwright, authentication, automatic data expiry, server-side retry, dependency vulnerability scans. Web research was limited to two searches (Ollama structured outputs, OWASP SSRF); other library behaviour was verified by running code, not by reading docs.

## Workspace caveat
The user's actual workspace was not accessible in this session, so `model-tests/.venv` and any existing frontend were not inspected. This project was created fresh; `model-tests/` here contains only new scripts and never a venv. When unzipping over your folder, keep your existing `model-tests\.venv`.

## Next actions
1. Follow `RUN_STEPS.md` on Windows; report any command that fails.
2. Run `model-tests\test_ollama.py` and record results in `ai-models-and-evaluation.md`.
3. Try a real job URL and a real public GitHub repo; try `EMBEDDING_BACKEND=sentence-transformers`.
4. Browser accessibility pass.
