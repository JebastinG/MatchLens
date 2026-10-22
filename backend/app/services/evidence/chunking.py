import re
from dataclasses import dataclass
from datetime import datetime

BULLET = re.compile(r"^[•●▪◦·\-\*–—]\s*")
BULLET_ONLY = re.compile(r"^[•●▪◦·\-\*–—]$")
MAX_CHARS = 500


@dataclass
class EvidenceChunk:
    ref: str
    source_type: str  # resume | github
    text: str
    page: int | None = None
    repo: str | None = None
    source_url: str | None = None
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    commit_sha: str | None = None
    retrieved_at: datetime | None = None


def norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + len(sent) + 1 > MAX_CHARS:
            parts.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        parts.append(cur)
    out = []
    for p in parts:  # hard split any remaining oversized sentence
        out.extend(p[i : i + MAX_CHARS] for i in range(0, len(p), MAX_CHARS))
    return out


def chunk_resume(pages: list[str]) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    for pno, page in enumerate(pages, start=1):
        blocks: list[str] = []
        buf: list[str] = []

        def flush(buf=buf, blocks=blocks):
            if buf:
                blocks.append(norm_ws(" ".join(buf)))
                buf.clear()

        for raw in page.splitlines():
            line = raw.strip()
            if not line:
                flush()
            elif BULLET_ONLY.match(line):
                flush()
            elif BULLET.match(line):
                flush()
                buf.append(BULLET.sub("", line))
            else:
                buf.append(line)
        flush()

        merged: list[str] = []
        carry = ""
        for b in blocks:
            if len(b) < 30 and not b.endswith("."):  # heading-like: attach to next block
                carry = f"{carry} {b}".strip()
                continue
            merged.append(f"{carry} {b}".strip() if carry else b)
            carry = ""
        if carry:
            merged.append(carry)

        n = 0
        for block in merged:
            for piece in _split_long(block):
                if len(piece) < 3:
                    continue
                n += 1
                chunks.append(
                    EvidenceChunk(ref=f"R-p{pno}-c{n}", source_type="resume", text=piece, page=pno)
                )
    return chunks


def chunk_code(text: str, window: int = 40) -> list[tuple[int, int, str]]:
    """Return (line_start, line_end, text) windows with 1-based inclusive lines."""
    lines = text.splitlines()
    out = []
    for i in range(0, len(lines), window):
        seg = lines[i : i + window]
        body = "\n".join(seg)
        if body.strip():
            out.append((i + 1, i + len(seg), body[:2000]))
    return out
