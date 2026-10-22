from app.workers.pipeline import Deps
from tests.conftest import run_and_get, submit


class FakeLLM:
    """Scripted stand-in for Ollama. Tests deterministic handling of untrusted model output."""

    def __init__(self, assess):
        self.assess, self.prompts = assess, []

    def check(self):
        return True, None, ["fake:1b"]

    def chat_json(self, system, user, schema, num_predict=600):
        self.prompts.append(user)
        props = schema["properties"]
        if "requirements" in props:
            return {"requirements": [{"text": "Experience with Python", "category": "required"},
                                     {"text": "Invented requirement about blockchain", "category": "required"}]}
        if "questions" in props:
            return {"questions": [{"requirement_id": "REQ-1", "question": "Describe a Python API you built.",
                                   "rationale": "Resume mentions Python."},
                                  {"requirement_id": "REQ-99", "question": "Bogus id question here.", "rationale": "x"}]}
        return self.assess(user)


def test_llm_path_validates_everything(make_client, settings):
    def assess(user):  # fabricates a quote and over-claims
        return {"status": "supported", "explanation": "Strong.",
                "evidence": [{"id": "R-p1-c5", "quote": "Led Kubernetes platform at a FAANG company"}]}
    llm = FakeLLM(assess)
    c = make_client(Deps(settings, llm=llm))
    _, res = run_and_get(c, submit(c))
    body = res.json()
    assert body["analysis"]["analysis_mode"] == "llm"
    assert any("not grounded" in w for w in body["analysis"]["warnings"])
    assert [r["text"] for r in body["requirements"]] == ["Experience with Python"]
    a = body["requirements"][0]["assessment"]
    assert a["status"] in ("uncertain", "needs_better_evidence") or a["method"] != "llm"
    assert "FAANG" not in str(body)  # fabricated quotation never surfaces
    assert [q["source"] for q in body["interview_questions"]] == ["llm"]  # bogus requirement id dropped


def test_llm_valid_quote_is_kept(make_client, settings):
    def assess(user):
        return {"status": "supported", "explanation": "Direct.",
                "evidence": [{"id": "R-p1-c2", "quote": "Built a REST API in Python with FastAPI"}]}
    c = make_client(Deps(settings, llm=FakeLLM(assess)))
    _, res = run_and_get(c, submit(c, job_mode="manual", job_description=None, manual_title="Dev",
                                   manual_requirements="Python"))
    a = res.json()["requirements"][0]["assessment"]
    assert a["status"] == "supported" and any(e["quote"] for e in a["evidence"]) or a["method"] == "deterministic"


def test_invalid_model_output_falls_back_to_rules(make_client, settings):
    c = make_client(Deps(settings, llm=FakeLLM(lambda u: "garbage")))
    _, res = run_and_get(c, submit(c, job_mode="manual", job_description=None, manual_title="Dev",
                                   manual_requirements="Python"))
    a = res.json()["requirements"][0]["assessment"]
    assert a["status"] == "supported" and a["method"] == "deterministic"
    assert any("invalid" in w for w in a["warnings"])


def test_unavailable_model_uses_rules_with_warning(make_client, settings):
    class Down:
        def check(self):
            return False, "Ollama is not reachable.", []
    c = make_client(Deps(settings, llm=Down()))
    _, res = run_and_get(c, submit(c))
    assert res.json()["analysis"]["analysis_mode"] == "deterministic"
    assert any("unavailable" in w for w in res.json()["analysis"]["warnings"])
