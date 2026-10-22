# model-tests

Scratch scripts for checking local models on **your** machine. Keep your existing `.venv` here; it is not touched by the backend.

- `python test_ollama.py` — lists installed models, runs a small structured-output check (valid JSON, verbatim quotes, latency) and prints loaded-model memory from `/api/ps`. Pass model names to restrict it.
- `python test_embeddings.py` — loads `all-MiniLM-L6-v2`, ranks sample chunks, prints timings. Use the cosine values to calibrate `min_related` before switching `EMBEDDING_BACKEND=sentence-transformers`.

Results are written to `test_results/` and then summarised by hand in `docs/ai-models-and-evaluation.md`.
