import json

import pytest

from app.services.jobs.parse import JobParseError, extract_job_from_html
from app.services.jobs.requirements import (
    extract_requirements_heuristic,
    requirements_from_manual,
    validate_llm_requirements,
)
from tests.conftest import JOB_TEXT


def test_heuristic_requirements_sections():
    reqs = extract_requirements_heuristic(JOB_TEXT, 25)
    texts = [r.text for r in reqs]
    assert "3+ years of experience with Python" in texts
    assert not any("logistics" in t for t in texts)  # 'About us' section skipped
    aws = next(r for r in reqs if "AWS" in r.text)
    assert aws.category == "preferred" and aws.key_terms == ["aws"]
    assert next(r for r in reqs if "Kubernetes" in r.text).category == "required"


def test_manual_requirements_one_per_line():
    reqs = requirements_from_manual("- Python\n- Docker\n\n- Python", 25)
    assert [r.text for r in reqs] == ["Python", "Docker"]


def test_llm_requirements_must_be_grounded():
    raw = {"requirements": [
        {"text": "Experience with Python", "category": "required"},
        {"text": "Ten years of quantum computing research", "category": "required"},
        {"text": 5},
    ]}
    kept, dropped = validate_llm_requirements(raw, "We need experience with Python daily.", 10)
    assert [r.text for r in kept] == ["Experience with Python"] and dropped == 2
    assert validate_llm_requirements("garbage", "x", 5) == ([], 0)


def test_html_jsonld_and_plain():
    ld = {"@type": "JobPosting", "title": "Data Engineer", "hiringOrganization": {"name": "Acme"},
          "description": "<ul><li>Experience with SQL</li><li>Python</li></ul><p>" + "More text. " * 30 + "</p>"}
    html = f'<html><script type="application/ld+json">{json.dumps(ld)}</script></html>'
    title, company, text = extract_job_from_html(html)
    assert (title, company) == ("Data Engineer", "Acme") and "- Experience with SQL" in text


def test_scripts_not_executed_or_included_and_js_only_page_rejected():
    html = "<html><body><script>alert(1)</script><h1>Role</h1><p>" + "Real text here. " * 30 + "</p></body></html>"
    _, _, text = extract_job_from_html(html)
    assert "alert" not in text and "Real text" in text
    with pytest.raises(JobParseError):
        extract_job_from_html("<html><body><div id='root'></div><script>load()</script></body></html>")
