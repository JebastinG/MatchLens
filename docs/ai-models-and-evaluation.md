# AI models and evaluation

## Status of each model (read this first)
| Component | Status |
|---|---|
| Ollama client (`/api/tags`, `/api/chat` with JSON-schema `format`, `temperature 0`) | Implemented and verified live on Windows against `http://127.0.0.1:11434` with schema-constrained structured output. |
| `qwen2.5:3b` (baseline model) | **Verified live in the application pipeline on Windows.** Successfully extracts structured requirements, produces valid JSON, and integrates with the matching workflow. |
| `deepseek-r1:8b`, `gemma4:e4b` | Supported alternative local models; formal benchmark comparisons not yet recorded. |
| `sentence-transformers/all-MiniLM-L6-v2` | Optional backend wired in; **never loaded** (no Hugging Face access in the sandbox). Default retrieval is lexical. |

**No latency, memory or quality numbers exist for any LLM or embedding model.** Run `model-tests/test_ollama.py` and `test_embeddings.py` on your machine, then record the numbers below.

| Model | Valid JSON | Verbatim quotes | s / requirement | RAM (`/api/ps`) | Notes |
|---|---|---|---|---|---|
| _fill in after running_ | | | | | |

## Safeguards that do not depend on model quality
Ollama enforces the output schema; `validate.py` then rejects unknown statuses, unknown evidence ids and quotations that are not substrings of the cited excerpt; claims the rules cannot corroborate are downgraded; model-proposed requirements must be ≥70% grounded in the job text; interview questions must reference a real requirement id. Covered by unit/integration tests using a scripted fake LLM.

## Rule-layer regression set (measured)
`tests/evaluation/run_eval.py`: 10 synthetic requirements against one synthetic resume, rule layer only, lexical retrieval. Result: **10/10 agree**. Caveat: one label (Airflow) was changed from `no_evidence_found` to `uncertain` after seeing the output, so agreement is partly circular. This is a regression guard, **not** an accuracy benchmark; no real resumes or job posts were evaluated.

## Known limitations
Skill lexicon has ~50 entries; requirements outside it cannot be rule-verified. "All vs any" logic is a keyword heuristic. Lexical retrieval has no semantic understanding. `min_related` thresholds are uncalibrated (0.34 lexical, 0.30 cosine). LLM assessment is limited to the first `LLM_MAX_REQUIREMENTS` (20). Small local models can be wrong even with valid JSON; validation catches fabricated quotes, not subtle misjudgements.
