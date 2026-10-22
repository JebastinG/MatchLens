import re
from dataclasses import dataclass

from app.services.embeddings.embedder import tokenize
from app.services.evidence.skills import find_terms

REQ_HEAD = re.compile(
    r"^(requirements?|qualifications?|what you('|’)ll need|what we('|’)re looking for|must[- ]have|"
    r"basic qualifications|minimum qualifications|skills|you have|about you)\b", re.I)
PREF_HEAD = re.compile(r"^(preferred|nice[- ]to[- ]have|bonus|good to have|a plus|desired|"
                       r"preferred qualifications)\b", re.I)
SKIP_HEAD = re.compile(r"^(responsibilities|what you('|’)ll do|about (us|the (role|team|company))|"
                       r"benefits|perks|we offer|compensation|our (mission|culture))\b", re.I)
BULLET = re.compile(r"^\s*(?:[-*•●▪◦·–]|\d+[.)])\s+")
CUE = re.compile(r"\b(experience|proficien\w*|knowledge|familiar\w*|ability|able to|years?|degree|"
                 r"understanding|expertise|skilled|background in)\b", re.I)


@dataclass
class Req:
    text: str
    category: str = "unspecified"
    key_terms: list[str] | None = None


def _finish(items: list[Req], limit: int) -> list[Req]:
    seen, out = set(), []
    for r in items:
        text = re.sub(r"\s+", " ", r.text).strip(" -•*\t")
        key = text.lower()
        if len(text) < 4 or key in seen:
            continue
        seen.add(key)
        out.append(Req(text[:300], r.category, find_terms(text)))
        if len(out) >= limit:
            break
    return out


def extract_requirements_heuristic(job_text: str, limit: int) -> list[Req]:
    section, items, sections_seen = "unspecified", [], False
    for raw in job_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        bare = BULLET.sub("", line).rstrip(":").strip()
        is_head = (not BULLET.match(raw)) and len(bare) < 60 and (
            line.endswith(":") or REQ_HEAD.match(bare) or PREF_HEAD.match(bare) or SKIP_HEAD.match(bare)
        )
        if is_head:
            if PREF_HEAD.match(bare):
                section, sections_seen = "preferred", True
            elif SKIP_HEAD.match(bare):
                section = "skip"
            elif REQ_HEAD.match(bare):
                section, sections_seen = "required", True
            else:
                section = "unspecified" if section == "skip" else section
            continue
        if section == "skip":
            continue
        if sections_seen and section in ("required", "preferred"):
            if BULLET.match(raw) or CUE.search(line) or find_terms(line):
                items.extend(Req(s, section) for s in _sentences(bare))
        elif BULLET.match(raw) and (CUE.search(line) or find_terms(line)):
            items.extend(Req(s, "unspecified") for s in _sentences(bare))
    if not items:  # unstructured text: fall back to sentences with requirement cues
        for s in re.split(r"(?<=[.!?])\s+|\n", job_text):
            if CUE.search(s) or find_terms(s):
                items.append(Req(s.strip(), "unspecified"))
    return _finish(items, limit)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;])\s+(?=[A-Z])", text) if s.strip()]


def requirements_from_manual(text: str, limit: int) -> list[Req]:
    items = [Req(BULLET.sub("", ln), "required") for ln in text.splitlines() if ln.strip()]
    return _finish(items, limit)


def validate_llm_requirements(raw: object, job_text: str, limit: int) -> tuple[list[Req], int]:
    """Keep only requirements that are grounded in the job text. Returns (reqs, dropped)."""
    if not isinstance(raw, dict) or not isinstance(raw.get("requirements"), list):
        return [], 0
    job_tokens = set(tokenize(job_text))
    kept, dropped = [], 0
    for item in raw["requirements"]:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            dropped += 1
            continue
        text = re.sub(r"</?\s*(excerpt|requirement|job_text)[^>]*>", "", item["text"], flags=re.I).strip()
        toks = tokenize(text)
        grounded = bool(toks) and sum(t in job_tokens for t in toks) / len(toks) >= 0.7
        if not (4 <= len(text) <= 300) or not grounded:
            dropped += 1
            continue
        cat = item.get("category")
        kept.append(Req(text, cat if cat in ("required", "preferred") else "unspecified"))
    return _finish(kept, limit), dropped
