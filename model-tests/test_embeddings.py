"""Check that sentence-transformers/all-MiniLM-L6-v2 loads and ranks sensibly; time it on this machine.
Run inside model-tests/.venv:  python test_embeddings.py   (first run downloads the model from Hugging Face)
"""
import json
import pathlib
import time

from sentence_transformers import SentenceTransformer

NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNKS = [
    "Built a REST API in Python with FastAPI serving 40 internal users.",
    "Designed PostgreSQL schemas and optimized slow SQL queries.",
    "Containerized services with Docker and automated deployments.",
    "Led a team of 3 engineers during a migration project.",
]
QUERIES = ["Experience with Python web APIs", "Database design experience", "Kubernetes orchestration", "Leadership of small teams"]

t0 = time.perf_counter()
model = SentenceTransformer(NAME)
load_s = time.perf_counter() - t0
t0 = time.perf_counter()
emb = model.encode(CHUNKS, normalize_embeddings=True)
q = model.encode(QUERIES, normalize_embeddings=True)
enc_s = time.perf_counter() - t0
rows = []
for qi, qt in enumerate(QUERIES):
    sims = emb @ q[qi]
    best = int(sims.argmax())
    rows.append({"query": qt, "best_chunk": CHUNKS[best], "cosine": round(float(sims[best]), 3), "all": [round(float(s), 3) for s in sims]})
    print(f"{qt!r:42} -> {sims[best]:.3f}  {CHUNKS[best]}")
out = pathlib.Path(__file__).parent / "test_results"
out.mkdir(exist_ok=True)
(out / "embeddings.json").write_text(json.dumps({"model": NAME, "load_seconds": round(load_s, 2), "encode_seconds": round(enc_s, 3), "rows": rows}, indent=2))
print(f"load {load_s:.1f}s, encode {enc_s:.3f}s  (use these cosine values to calibrate SentenceTransformerRanker.min_related)")
