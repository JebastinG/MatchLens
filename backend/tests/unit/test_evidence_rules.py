from app.services.embeddings.embedder import LexicalRanker
from app.services.evidence.assess import assess_rules, score_chunks
from app.services.evidence.chunking import EvidenceChunk, chunk_resume
from app.services.evidence.skills import find_terms, is_skill_listing
from app.services.evidence.validate import quote_in, reconcile, validate_llm_assessment

PAGES = ["Alex\nSkills: Python, SQL, Docker, Git, Linux\nExperience\n• Built a REST API in Python with "
         "FastAPI for 40 users.\n•\nDesigned PostgreSQL schemas for a reporting service.\n"]


def _run(req, terms, extra=None):
    chunks = chunk_resume(PAGES) + (extra or [])
    r = LexicalRanker()
    r.fit([c.text for c in chunks])
    return assess_rules(req, terms, score_chunks(chunks, r.score(req)), r.min_related)


def test_chunking_keeps_page_and_exact_text():
    ch = chunk_resume(PAGES)
    assert all(c.page == 1 and c.ref.startswith("R-p1-c") for c in ch)
    assert any(c.text.startswith("Built a REST API in Python") for c in ch)


def test_find_terms_word_boundaries():
    assert find_terms("Java and JavaScript") == ["java", "javascript"]
    assert "java" not in find_terms("JavaScript only")
    assert "c++" in find_terms("C++ and C#") and "c#" in find_terms("C++ and C#")
    assert "go" not in find_terms("go to market")


def test_supported_requires_context_not_just_listing():
    a = _run("Experience with Python", ["python"])
    assert a.status == "supported" and any("FastAPI" in c.text for c, _ in a.evidence)
    b = _run("Experience with Linux", ["linux"])
    assert b.status == "needs_better_evidence" and "listed" in b.explanation


def test_related_and_no_evidence_wording():
    assert _run("Experience with MySQL", ["mysql"]).status == "related_skill_found"
    a = _run("Experience with Kubernetes", ["kubernetes"])
    assert a.status == "related_skill_found" or a.status == "no_evidence_found"
    n = _run("Experience with Terraform", ["terraform"])
    assert n.status == "no_evidence_found" and "does not show" in n.explanation and not n.evidence


def test_all_vs_any_semantics():
    assert _run("Python and Terraform", ["python", "terraform"]).status == "needs_better_evidence"
    assert _run("Python or Terraform", ["python", "terraform"]).status == "supported"


def test_github_only_is_never_direct_support_and_carries_warning():
    gh = EvidenceChunk(ref="G-x", source_type="github", text="import terraform_wrapper\nterraform apply",
                       repo="a/b", path="main.tf", line_start=1, line_end=2)
    a = _run("Experience with Terraform", ["terraform"], [gh])
    assert a.status == "needs_better_evidence" and any("authorship" in w for w in a.warnings)


def test_requirement_without_keywords_is_uncertain_or_no_evidence_never_supported():
    a = _run("Led a team of engineers", [])
    assert a.status in ("uncertain", "no_evidence_found")
    assert _run("Strong quantum chromodynamics background", []).status == "no_evidence_found"


def test_skill_listing_detection():
    assert is_skill_listing("Skills: Python, SQL")
    assert not is_skill_listing("Built a REST API in Python with FastAPI for 40 users.")


# --- LLM output validation -------------------------------------------------------------------------
CH = EvidenceChunk(ref="R-p1-c2", source_type="resume", text="Built a REST API in Python with FastAPI.", page=1)
ALLOWED = {CH.ref: CH}


def test_fabricated_quote_is_discarded_and_status_downgraded():
    raw = {"status": "supported", "explanation": "Shown.",
           "evidence": [{"id": "R-p1-c2", "quote": "Led Kubernetes migrations at Google"}]}
    a = validate_llm_assessment(raw, ALLOWED)
    assert a.status == "uncertain" and not a.evidence and a.warnings


def test_unknown_id_and_bad_status_rejected():
    assert validate_llm_assessment({"status": "great", "explanation": "x", "evidence": []}, ALLOWED) is None
    raw = {"status": "supported", "explanation": "x", "evidence": [{"id": "R-p9-c9", "quote": "Python with FastAPI"}]}
    assert validate_llm_assessment(raw, ALLOWED).status == "uncertain"


def test_valid_quote_accepted_case_and_whitespace_insensitive():
    assert quote_in("built a  REST API", CH.text)
    raw = {"status": "supported", "explanation": "Direct.", "evidence": [{"id": CH.ref, "quote": "Built a REST API in Python"}]}
    a = validate_llm_assessment(raw, ALLOWED)
    assert a.status == "supported" and a.evidence[0][1] == "Built a REST API in Python"


def test_no_evidence_found_drops_citations():
    raw = {"status": "no_evidence_found", "explanation": "None.", "evidence": [{"id": CH.ref, "quote": "Built a REST API"}]}
    assert validate_llm_assessment(raw, ALLOWED).evidence == []


def test_reconcile_never_upgrades_beyond_rules():
    det = _run("Experience with Terraform", ["terraform"])
    raw = {"status": "supported", "explanation": "ok", "evidence": [{"id": CH.ref, "quote": "Built a REST API in Python"}]}
    out = reconcile(det, validate_llm_assessment(raw, ALLOWED))
    assert out.status == "uncertain" and out.method == "reconciled"
    det2 = _run("Experience with Python", ["python"])
    llm_none = validate_llm_assessment({"status": "no_evidence_found", "explanation": "n", "evidence": []}, ALLOWED)
    assert reconcile(det2, llm_none).status == "uncertain"
