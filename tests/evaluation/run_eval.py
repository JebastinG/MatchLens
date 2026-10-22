"""Rule-layer regression evaluation on synthetic labeled cases (no network, no LLM).

Run from the repo root with the BACKEND venv active:
    python tests/evaluation/run_eval.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.embeddings.embedder import LexicalRanker  # noqa: E402
from app.services.evidence.assess import assess_rules, score_chunks  # noqa: E402
from app.services.evidence.chunking import chunk_resume  # noqa: E402
from app.services.evidence.skills import find_terms  # noqa: E402

data = json.loads((pathlib.Path(__file__).parent / "labeled_cases.json").read_text())
chunks = chunk_resume(["\n".join(data["resume_lines"])])
ranker = LexicalRanker()
ranker.fit([c.text for c in chunks])

ok = 0
for case in data["requirements"]:
    res = assess_rules(case["text"], find_terms(case["text"]), score_chunks(chunks, ranker.score(case["text"])), ranker.min_related)
    hit = res.status == case["expected"]
    ok += hit
    print(f"{'PASS' if hit else 'FAIL'}  expected={case['expected']:<22} got={res.status:<22} {case['text']}")
print(f"\nagreement: {ok}/{len(data['requirements'])}")
sys.exit(0 if ok == len(data["requirements"]) else 1)
