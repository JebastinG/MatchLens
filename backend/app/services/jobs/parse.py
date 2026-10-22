import json
import re

from bs4 import BeautifulSoup

MAX_JOB_CHARS = 30_000
MIN_JOB_CHARS = 200


class JobParseError(Exception):
    pass


def _clean(text: str) -> str:
    text = text.replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    out: list[str] = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return "\n".join(out).strip()


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")  # parsing only; nothing is executed
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for br in soup.find_all(["br", "p", "div", "h1", "h2", "h3", "h4", "tr"]):
        br.insert_after("\n")
    return _clean(soup.get_text())


def _jobposting(soup: BeautifulSoup) -> dict | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for item in items:
            if isinstance(item, dict) and "JobPosting" in str(item.get("@type")):
                return item
    return None


def extract_job_from_html(html: str) -> tuple[str | None, str | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = company = None
    jp = _jobposting(soup)
    if jp and jp.get("description"):
        title = str(jp.get("title") or "") or None
        org = jp.get("hiringOrganization")
        company = (org.get("name") if isinstance(org, dict) else None) or None
        text = _html_to_text(str(jp["description"]))
    else:
        for t in soup(["script", "style", "noscript", "svg", "nav", "header", "footer", "form"]):
            t.decompose()
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else (soup.title.string if soup.title else None)
        text = _html_to_text(str(soup.body or soup))
    text = text[:MAX_JOB_CHARS]
    if len(text) < MIN_JOB_CHARS:
        raise JobParseError(
            "Not enough job text was found on that page. It may require JavaScript or a login. "
            "Paste the job description instead."
        )
    return (title[:300] if title else None), (company[:300] if company else None), text
