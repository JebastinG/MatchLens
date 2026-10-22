# Testing plan

| Layer | Command | Needs | Expected |
|---|---|---|---|
| Backend unit/integration/security | `cd backend; pytest` | nothing external (SQLite temp DB, mocked HTTP, fake LLM) | 85 passed |
| PostgreSQL integration | `$env:TEST_DATABASE_URL=…; pytest -m integration` | migrated PostgreSQL | 1 passed |
| Lint | `ruff check app tests` | — | clean |
| Migration | `alembic upgrade head; alembic check; alembic downgrade base; alembic upgrade head` | PostgreSQL | no errors, "No new upgrade operations" |
| Rule regression | `python tests\evaluation\run_eval.py` | backend venv | 10/10 (see caveat in AI doc) |
| Frontend | `npm run typecheck; npm test; npm run build` | Node | clean / 4 passed / build OK |
| Model checks (manual) | `model-tests\test_ollama.py`, `test_embeddings.py` | Ollama / HF download | numbers recorded in AI doc |
| Manual UI | follow `setup-windows.md` §5 with a synthetic resume | all services | stages progress, results show evidence, dismiss/delete work |

Optional/not automated: real job URLs, real GitHub API, real Ollama end-to-end, browser accessibility audit (axe/screen reader), responsive visual check. Test inputs are synthetic (generated PDFs); do not use real personal data in tests.
