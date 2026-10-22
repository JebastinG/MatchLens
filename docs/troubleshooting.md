# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health` returns 503 `database_unavailable` | wrong `DATABASE_URL`/password, DB not running | check `.env`; `psql` with the same credentials; `docker compose ps` |
| `alembic upgrade` auth error | `MIGRATION_DATABASE_URL` uses wrong role/password, or roles not created | run step 1 (roles) first; owner role must own `public` schema |
| `permission denied for table` at runtime | tables created by a different role than `matchlens_owner` | re-run migrations as the owner role on a fresh database |
| Activate.ps1 "running scripts is disabled" | PowerShell policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Browser: CORS error / "Cannot reach backend" | backend not running, wrong `VITE_API_BASE_URL`, or frontend on a port not in `CORS_ORIGINS` | start backend; fix env; restart `npm run dev` |
| Results say "rule-based (local model not used)" | Ollama down, model name mismatch, or `LLM_ENABLED=false` | open `/api/v1/health/ai`; match `OLLAMA_MODEL` to `ollama list`; start `ollama serve` |
| Very slow analysis | large/reasoning model on CPU | use a smaller model; lower `LLM_MAX_REQUIREMENTS`; check `ollama ps` |
| 422 `pdf_no_text` | scanned/image PDF | export a text-based PDF (no OCR support) |
| 502 `job_page_unavailable` for a valid page | JavaScript-rendered/login page, or blocked address | paste the text instead |
| GitHub warning "rate limit reached" | unauthenticated 60 requests/hour | set `GITHUB_TOKEN` (public read-only) |
| Analysis stuck `queued` | worker disabled (`RUN_WORKER=false`) or API restarted | set `RUN_WORKER=true`; restart (interrupted jobs are requeued up to 2 attempts) |
| `pip install` fails on Python 3.14 | wheels not available for some deps | use Python 3.11/3.12 |
