# Architecture decisions

| Decision | Alternatives | Why / trade-off |
|---|---|---|
| Modular monolith + in-process worker thread | Celery+Redis, separate worker service | One machine, one user: fewer moving parts. Trade-off: worker dies with the API (handled by `recover_interrupted`). Single thread also caps concurrent LLM inference at 1. |
| DB-backed queue (`status='queued'` + atomic UPDATE claim) | In-memory queue | Survives restarts; attempts are bounded (`WORKER_MAX_ATTEMPTS`). Trade-off: polling every 1 s; one worker only (no multi-process claim contention testing). |
| Rules first, LLM second, validation always | LLM decides everything | The LLM can only refine, never exceed what quotes + rules support; fabricated quotes are dropped; disagreement → `uncertain`. Costs some recall. |
| Lexical retrieval by default | MiniLM embeddings by default | Works offline with zero downloads and is deterministic for tests. MiniLM is wired in but **untested here**; embeddings measure similarity, never proficiency. |
| Resume PDF validated synchronously at POST | Validate in worker | Immediate 413/415/422 feedback. Trade-off: extraction runs twice (cheap). |
| Job URL fetched synchronously at POST (502 on failure) | Fetch in worker | Immediate feedback, no half-created analyses. Bounded by 10 s timeout. |
| Pinned-IP fetching with per-hop validation | Plain `httpx` with redirects | Mitigates DNS rebinding; trade-off: custom code (`services/jobs/fetch.py`) that must be maintained. |
| Uploaded PDF deleted after processing | Keep for retries | Minimal retention. Trade-off: a failed analysis cannot be retried server-side; the UI keeps form inputs so the user resubmits. |
| Plain CSS + lucide-react frontend | shadcn/ui + Radix + Tailwind | The brief asked for shadcn/Radix "where compatible". Not used: the UI needs few primitives (tabs, dialog, details) that native HTML/ARIA cover, avoiding a large toolchain. Trade-off: less ready-made polish. |
| No Playwright | Render JS-heavy job pages | No demonstrated need; unreadable pages return a clear 502 asking the user to paste text. |
| No confidence numbers | Show model confidence | No calibration exists; `confidence` is always `null`. |
| Explainable metrics (`direct_support_share`, `evidence_coverage_share`) | Single "match score" | Explicitly defined, non-predictive; displayed with a disclaimer. |
