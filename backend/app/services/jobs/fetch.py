import ipaddress
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.utils.ssrf import Resolver, UnsafeURL, resolve_public, validate_url

ALLOWED_CTYPES = ("text/html", "application/xhtml+xml", "text/plain")


class JobFetchError(Exception):
    """Retrieval failed (network, status, size, type). Message is safe to show."""


@dataclass
class FetchResult:
    final_url: str
    body: str


def fetch_public_page(
    url: str,
    settings: Settings,
    resolver: Resolver | None = None,
    transport: httpx.BaseTransport | None = None,
) -> FetchResult:
    current = url.strip()
    for _hop in range(settings.job_max_redirects + 1):
        try:
            scheme, host, port = validate_url(current)
            ip = resolve_public(host, port, resolver)[0]
        except UnsafeURL as exc:
            raise JobFetchError(str(exc)) from exc

        ip_host = f"[{ip}]" if ipaddress.ip_address(ip).version == 6 else ip
        default_port = 443 if scheme == "https" else 80
        pinned = f"{scheme}://{ip_host}:{port}" + _path_and_query(current)
        headers = {
            "Host": host if port == default_port else f"{host}:{port}",
            "User-Agent": "MatchLens/0.1 (+local job-page reader)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8",
        }
        timeout = httpx.Timeout(settings.job_fetch_timeout_s, connect=5.0)
        try:
            with httpx.Client(timeout=timeout, transport=transport, trust_env=False) as client:
                with client.stream(
                    "GET",
                    pinned,
                    headers=headers,
                    extensions={"sni_hostname": host},
                    follow_redirects=False,
                ) as resp:
                    if 300 <= resp.status_code < 400:
                        loc = resp.headers.get("location")
                        if not loc:
                            raise JobFetchError("Redirect without a Location header.")
                        current = urljoin(current, loc)
                        continue
                    if resp.status_code != 200:
                        raise JobFetchError(f"The job page returned HTTP {resp.status_code}.")
                    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                    if ctype not in ALLOWED_CTYPES:
                        raise JobFetchError("The URL did not return an HTML or text page.")
                    buf = bytearray()
                    for chunk in resp.iter_bytes():
                        buf.extend(chunk)
                        if len(buf) > settings.job_max_bytes:
                            raise JobFetchError("The job page is too large.")
                    return FetchResult(current, buf.decode(resp.encoding or "utf-8", "replace"))
        except httpx.TimeoutException as exc:
            raise JobFetchError("The job page timed out.") from exc
        except httpx.HTTPError as exc:
            raise JobFetchError("The job page could not be retrieved.") from exc
    raise JobFetchError("Too many redirects.")


def _path_and_query(url: str) -> str:
    from urllib.parse import urlsplit

    p = urlsplit(url)
    out = p.path or "/"
    return out + (f"?{p.query}" if p.query else "")
