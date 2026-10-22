# Limitations and future work

## Known limitations
- Untested on Windows, with real Ollama models, MiniLM embeddings, real job sites, the live GitHub API, Docker Compose, or in a browser. See implementation-status.
- No authentication/multi-user isolation; local single-user tool.
- No OCR; scanned PDFs rejected. Multi-column/table PDFs may extract in odd order.
- Rule layer knows ~50 skills; other requirements rely on retrieval + optional LLM.
- Job URL support is static HTML + JSON-LD only; no JavaScript rendering.
- No automatic data expiry; no retry of failed analyses without resubmission.
- shadcn/Radix and MagicMouse not implemented; no charts (counts are shown as cards).
- LLM quality, latency and memory unknown until measured.

## Prioritised improvements
1. Run and record real model benchmarks; calibrate retrieval thresholds; evaluate on consented real samples.
2. Optional auth / per-session ownership and retention auto-expiry.
3. Browser/accessibility audit (axe, screen readers) and Playwright UI tests.
4. Expand the skill lexicon/relationships (data-driven, user-extensible).
5. Optional OCR (Tesseract) with explicit labelling.
6. Server-side retry with encrypted short-lived upload retention (opt-in).
7. Dependency scanning in CI; `pip-audit`, `npm audit`.
