"""Deterministic (rule-based) requirement assessment. Always runs; the LLM may refine it."""
import re
from dataclasses import dataclass, field

from app.services.evidence.chunking import EvidenceChunk
from app.services.evidence.skills import RELATED, find_terms, is_skill_listing

GITHUB_NOTE = (
    "Repository content shows the technology appears in public code. It does not prove "
    "authorship or proficiency."
)


@dataclass
class Scored:
    chunk: EvidenceChunk
    score: float
    terms: list[str]
    listing: bool = False


@dataclass
class Assessment:
    status: str
    explanation: str
    evidence: list[tuple[EvidenceChunk, str | None]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    method: str = "deterministic"


def score_chunks(chunks: list[EvidenceChunk], scores: list[float]) -> list[Scored]:
    out = []
    for c, s in zip(chunks, scores, strict=True):
        out.append(Scored(c, s, find_terms(c.text), is_skill_listing(c.text) if c.page else False))
    return out


def uses_any_semantics(text: str) -> bool:
    return bool(re.search(r"\b(or|and/or)\b|/", text, re.I))


def _fmt(terms) -> str:
    return ", ".join(sorted(terms))


def assess_rules(req_text: str, key_terms: list[str], scored: list[Scored], min_related: float) -> Assessment:
    terms = set(key_terms)
    ranked = sorted(scored, key=lambda s: -s.score)
    if terms:
        any_sem = uses_any_semantics(req_text)
        hits = [s for s in ranked if terms & set(s.terms)]
        covered = set().union(*(terms & set(s.terms) for s in hits)) if hits else set()
        sub = [
            s for s in hits
            if s.chunk.source_type == "resume" and not s.listing and len(s.chunk.text) >= 40
        ]
        sub_cov = set().union(*(terms & set(s.terms) for s in sub)) if sub else set()
        complete = bool(sub_cov) if any_sem else sub_cov == terms
        if complete:
            ev = sub[:3] + [s for s in hits if s.chunk.source_type == "github"][:1]
            return Assessment(
                "supported",
                f"The resume describes work involving {_fmt(sub_cov)} in context "
                f"({len(sub)} matching passage{'s' if len(sub) != 1 else ''}).",
                [(s.chunk, None) for s in ev],
                [GITHUB_NOTE] if any(s.chunk.source_type == "github" for s in ev) else [],
            )
        if hits:
            warnings, why = [], []
            if any(s.chunk.source_type == "github" for s in hits) and not sub:
                warnings.append(GITHUB_NOTE)
            if sub_cov and sub_cov != terms:
                missing = terms - sub_cov
                why.append(f"Demonstrated in the resume: {_fmt(sub_cov)}. "
                           f"No evidence found for: {_fmt(missing)}.")
            elif hits and all(s.listing for s in hits if s.chunk.source_type == "resume") and any(
                s.chunk.source_type == "resume" for s in hits
            ):
                why.append(f"{_fmt(covered)} is listed on the resume but no project or role "
                           "context shows how it was used.")
            elif not sub:
                why.append(f"{_fmt(covered)} appears only in public repository content; the "
                           "resume does not describe using it.")
            return Assessment("needs_better_evidence", " ".join(why) or "Mention found without detail.",
                              [(s.chunk, None) for s in hits[:3]], warnings)
        rel = [s for s in ranked if any(RELATED.get(t, set()) & set(s.terms) for t in terms)]
        if rel:
            rel_terms = set().union(*(set(s.terms) for s in rel[:3])) & set().union(
                *(RELATED.get(t, set()) for t in terms))
            warnings = [GITHUB_NOTE] if any(s.chunk.source_type == "github" for s in rel[:3]) else []
            return Assessment(
                "related_skill_found",
                f"No direct mention of {_fmt(terms)} was found, but related skills appear: "
                f"{_fmt(rel_terms)}. Related is not equivalent.",
                [(s.chunk, None) for s in rel[:3]], warnings,
            )
        return Assessment(
            "no_evidence_found",
            f"No passage in the sources examined mentions {_fmt(terms)} or closely related skills. "
            "This does not show that the skill is absent.",
        )
    best = ranked[0] if ranked else None
    if best and best.score >= min_related:
        return Assessment(
            "uncertain",
            "Topically similar text was retrieved, but this requirement has no checkable keyword. "
            "Review the passages manually or enable the local LLM.",
            [(s.chunk, None) for s in ranked[:3] if s.score >= min_related],
        )
    return Assessment(
        "no_evidence_found",
        "No passage in the sources examined appears relevant. This does not show the skill is absent.",
    )
