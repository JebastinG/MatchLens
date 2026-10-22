# Limitations and future work

## Known limitations
- Tested on Windows with local PostgreSQL, React/Vite UI in the browser, and real Ollama (`qwen2.5:3b`). Still unverified with alternate Ollama models (`deepseek-r1:8b`, `gemma4:e4b`), MiniLM embeddings, live internet job site/GitHub fetching, or Docker Compose. See `docs/implementation-status.md`.
- No authentication/multi-user isolation; local single-user tool.
- No OCR; scanned PDFs rejected. Multi-column/table PDFs may extract in odd order.
- Rule layer knows ~50 skills; other requirements rely on retrieval + optional LLM.
- Job URL support is static HTML + JSON-LD only; no JavaScript rendering.
- No automatic data expiry; no retry of failed analyses without resubmission.
- shadcn/Radix and MagicMouse not implemented; no charts (counts are shown as cards).
- LLM quality verified for `qwen2.5:3b`; latency and memory benchmarks for additional models remain to be recorded.

## Prioritised improvements
1. Run and record real model benchmarks; calibrate retrieval thresholds; evaluate on consented real samples.
2. Optional auth / per-session ownership and retention auto-expiry.
3. Browser/accessibility audit (axe, screen readers) and Playwright UI tests.
4. Expand the skill lexicon/relationships (data-driven, user-extensible).
5. Optional OCR (Tesseract) with explicit labelling.
6. Server-side retry with encrypted short-lived upload retention (opt-in).
7. Dependency scanning in CI; `pip-audit`, `npm audit`.
