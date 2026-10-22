"""Validation of LLM output against retrieved source material.

The LLM is never trusted: status values, evidence ids and quotations are all verified.
"""
from app.models import EVIDENCE_STATUSES
from app.services.evidence.assess import Assessment
from app.services.evidence.chunking import EvidenceChunk, norm_ws

NEEDS_EVIDENCE = {"supported", "needs_better_evidence", "related_skill_found"}


def quote_in(quote: str, text: str) -> bool:
    q = norm_ws(quote).casefold()
    return len(q) >= 8 and q in norm_ws(text).casefold()


def validate_llm_assessment(raw: object, allowed: dict[str, EvidenceChunk]) -> Assessment | None:
    """Return a sanitized Assessment, or None if the response is unusable."""
    if not isinstance(raw, dict):
        return None
    status, expl = raw.get("status"), raw.get("explanation")
    if status not in EVIDENCE_STATUSES or not isinstance(expl, str) or not expl.strip():
        return None
    warnings, evidence, seen = [], [], set()
    for item in raw.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        ref, quote = item.get("id"), item.get("quote")
        chunk = allowed.get(ref) if isinstance(ref, str) else None
        if chunk is None:
            warnings.append("The model cited an unknown evidence id; it was discarded.")
            continue
        if not isinstance(quote, str) or not quote_in(quote, chunk.text):
            warnings.append(f"A quotation for {ref} could not be verified and was discarded.")
            continue
        if ref not in seen:
            seen.add(ref)
            evidence.append((chunk, norm_ws(quote)))
    if status in NEEDS_EVIDENCE and not evidence:
        warnings.append("The model gave no verifiable evidence for its conclusion.")
        status = "uncertain"
    if status == "no_evidence_found" and evidence:
        evidence = []
    return Assessment(status, norm_ws(expl)[:600], evidence, warnings, method="llm")


def reconcile(det: Assessment, llm: Assessment | None) -> Assessment:
    """Combine rules and LLM conservatively. Disagreements become 'uncertain'."""
    if llm is None:
        return det
    out = Assessment(llm.status, llm.explanation, llm.evidence, list(llm.warnings), "llm")
    if det.status in ("supported", "needs_better_evidence", "related_skill_found") and (
        llm.status == "no_evidence_found"
    ):
        return Assessment(
            "uncertain",
            "The rule-based check found related text but the model found none. Please review "
            f"manually. Rule-based note: {det.explanation}",
            det.evidence, det.warnings + ["Rules and model disagreed."], "reconciled",
        )
    if llm.status == "supported" and det.status in ("no_evidence_found", "uncertain"):
        out.status = "uncertain"
        out.warnings.append("The model reported direct support that the rule-based check could "
                            "not confirm; downgraded to uncertain.")
        out.method = "reconciled"
    elif llm.status == "supported" and det.status != "supported":
        out.status = "needs_better_evidence"
        out.warnings.append("Model reported support but explicit keyword checks only partly "
                            "agree; downgraded to needs_better_evidence.")
        out.method = "reconciled"
    out.warnings = list(dict.fromkeys(out.warnings + [w for w in det.warnings if "GitHub" in w or "Repository" in w]))
    return out
