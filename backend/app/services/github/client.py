"""Bounded, read-only GitHub REST retrieval. Only api.github.com is contacted; no code is executed."""
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from app.core.config import Settings
from app.services.evidence.chunking import EvidenceChunk, chunk_code

API = "https://api.github.com"
NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?"
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cs", ".cpp", ".c", ".sql",
            ".md", ".yml", ".yaml", ".toml", ".dockerfile", ".tf"}
SKIP_PARTS = {"node_modules", "vendor", "dist", "build", ".git", "__pycache__", "venv", ".venv"}
SKIP_NAMES = ("package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml")


class GitHubError(Exception):
    pass


def parse_github_url(url: str) -> tuple[str, str | None]:
    """Return (owner, repo|None). Raises ValueError for anything that is not a plain GitHub URL."""
    p = urlsplit(url.strip())
    if p.scheme not in ("http", "https") or (p.hostname or "").lower() not in ("github.com", "www.github.com"):
        raise ValueError("Enter a public github.com profile or repository URL.")
    if p.username or p.password or (p.port not in (None, 80, 443)):
        raise ValueError("Invalid GitHub URL.")
    parts = [s for s in p.path.split("/") if s]
    if not parts or len(parts) > 2 and parts[2] not in ("tree", "blob"):
        raise ValueError("Enter a GitHub profile (github.com/user) or repository (github.com/user/repo).")
    owner = parts[0]
    repo = re.sub(r"\.git$", "", parts[1]) if len(parts) > 1 else None
    if not re.fullmatch(NAME, owner) or (repo and not re.fullmatch(NAME, repo)):
        raise ValueError("Invalid GitHub name.")
    return owner, repo


def _eligible(path: str, size: int, max_bytes: int) -> bool:
    low = path.lower()
    parts = set(low.split("/"))
    name = low.rsplit("/", 1)[-1]
    if parts & SKIP_PARTS or name in SKIP_NAMES or ".min." in name or size > max_bytes or size == 0:
        return False
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    return ext in CODE_EXT or name in ("dockerfile", "readme")


def _priority(path: str) -> tuple[int, int]:
    low = path.lower()
    return (0 if low.rsplit("/", 1)[-1].startswith("readme") else 1, low.count("/"))


def fetch_github_evidence(
    url: str, settings: Settings, transport: httpx.BaseTransport | None = None
) -> tuple[list[EvidenceChunk], list[str]]:
    """Returns (chunks, warnings). Never raises for remote failures; they become warnings."""
    warnings: list[str] = []
    try:
        owner, repo = parse_github_url(url)
    except ValueError as exc:
        return [], [str(exc)]
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "MatchLens/0.1"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    chunks: list[EvidenceChunk] = []
    with httpx.Client(timeout=15.0, headers=headers, transport=transport, trust_env=False) as c:

        def get(path: str, raw: bool = False, **params):
            h = {"Accept": "application/vnd.github.raw+json"} if raw else {}
            r = c.get(f"{API}{path}", params=params, headers=h)
            if r.status_code == 404:
                raise GitHubError("GitHub user or repository not found (or it is private).")
            if r.status_code in (403, 429):
                raise GitHubError("GitHub API rate limit reached; try later or set GITHUB_TOKEN.")
            r.raise_for_status()
            return r

        try:
            if repo:
                repos = [f"{owner}/{repo}"]
            else:
                lst = get(f"/users/{owner}/repos", sort="pushed", per_page=30, type="owner").json()
                repos = [x["full_name"] for x in lst if not x.get("fork") and not x.get("archived")]
                repos = repos[: settings.github_max_repos]
                if not repos:
                    return [], ["No eligible public repositories were found for that profile."]
            for full in repos:
                try:
                    chunks += _repo_chunks(get, full, settings)
                except GitHubError as exc:
                    warnings.append(f"{full}: {exc}")
        except GitHubError as exc:
            warnings.append(str(exc))
        except (httpx.HTTPError, ValueError, KeyError):
            warnings.append("GitHub could not be reached; analysis continued with the resume only.")
    if not chunks and not warnings:
        warnings.append("No usable repository files were found.")
    return chunks, warnings


def _repo_chunks(get, full: str, settings: Settings) -> list[EvidenceChunk]:
    meta = get(f"/repos/{full}").json()
    branch = meta["default_branch"]
    sha = get(f"/repos/{full}/commits/{branch}").json()["sha"]
    tree = get(f"/repos/{full}/git/trees/{sha}", recursive="1").json().get("tree", [])
    files = [t for t in tree if t.get("type") == "blob"
             and _eligible(t["path"], t.get("size", 0), settings.github_max_file_bytes)]
    files.sort(key=lambda t: _priority(t["path"]))
    out: list[EvidenceChunk] = []
    now = datetime.now(UTC)
    for t in files[: settings.github_max_files_per_repo]:
        text = get(f"/repos/{full}/contents/{t['path']}", raw=True, ref=sha).text
        for i, (a, b, body) in enumerate(chunk_code(text), start=1):
            out.append(EvidenceChunk(
                ref=f"G-{full}:{t['path']}#{i}", source_type="github", text=body, repo=full,
                source_url=f"https://github.com/{full}/blob/{sha}/{t['path']}#L{a}-L{b}",
                path=t["path"], line_start=a, line_end=b, commit_sha=sha, retrieved_at=now))
    return out
