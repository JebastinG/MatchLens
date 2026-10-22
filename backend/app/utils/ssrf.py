"""SSRF protections for user-supplied job URLs.

Every hop (initial URL and each redirect) is validated, the hostname is resolved,
every resolved address must be globally routable, and the request is then pinned
to the validated IP so a second DNS lookup cannot rebind to an internal address.
"""
import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

ALLOWED_PORTS = {80, 443}
Resolver = Callable[[str, int], list[str]]


class UnsafeURL(ValueError):
    pass


def default_resolver(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURL("Hostname could not be resolved.") from exc
    return list({i[4][0] for i in infos})


def check_ip(raw: str) -> str:
    addr = ipaddress.ip_address(raw.split("%")[0])
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        addr = mapped
    if not addr.is_global or addr.is_multicast:
        raise UnsafeURL("URL points to a non-public network address.")
    return str(addr)


def validate_url(url: str) -> tuple[str, str, int]:
    """Return (scheme, hostname, port) or raise UnsafeURL. Does no network I/O."""
    if len(url) > 2000:
        raise UnsafeURL("URL is too long.")
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        raise UnsafeURL("Only http and https URLs are allowed.")
    if parts.username or parts.password:
        raise UnsafeURL("URLs with embedded credentials are not allowed.")
    host = parts.hostname
    if not host:
        raise UnsafeURL("URL has no hostname.")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeURL("URL has an invalid port.") from exc
    if port not in ALLOWED_PORTS:
        raise UnsafeURL("Only ports 80 and 443 are allowed.")
    return parts.scheme, host, port


def resolve_public(host: str, port: int, resolver: Resolver | None = None) -> list[str]:
    try:
        ipaddress.ip_address(host)
        candidates = [host]
    except ValueError:
        candidates = (resolver or default_resolver)(host, port)
    if not candidates:
        raise UnsafeURL("Hostname could not be resolved.")
    return [check_ip(c) for c in candidates]  # all addresses must be public
