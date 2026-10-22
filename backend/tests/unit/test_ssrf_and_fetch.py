import httpx
import pytest

from app.core.config import Settings
from app.services.jobs.fetch import JobFetchError, fetch_public_page
from app.utils.ssrf import UnsafeURL, resolve_public, validate_url


@pytest.mark.parametrize("url", [
    "ftp://example.com/x", "file:///etc/passwd", "http://user:pw@example.com/", "http://example.com:8080/",
    "http:///nohost", "javascript:alert(1)", "http://example.com:99999/",
])
def test_validate_url_rejects(url):
    with pytest.raises(UnsafeURL):
        validate_url(url)


@pytest.mark.parametrize("ip", [
    "127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.1", "169.254.169.254", "0.0.0.0", "::1",
    "100.64.0.1", "::ffff:127.0.0.1", "fc00::1", "fe80::1", "224.0.0.1",
])
def test_private_addresses_blocked(ip):
    with pytest.raises(UnsafeURL):
        resolve_public(ip, 80)


def test_hostname_resolving_to_any_private_address_is_blocked():
    with pytest.raises(UnsafeURL):
        resolve_public("evil.test", 80, lambda h, p: ["93.184.216.34", "10.0.0.1"])


def test_public_ip_allowed():
    assert resolve_public("ok.test", 443, lambda h, p: ["93.184.216.34"]) == ["93.184.216.34"]


S = Settings(job_max_bytes=2000)


def _resolver(mapping):
    return lambda host, port: mapping[host]


def test_redirect_to_internal_host_is_blocked():
    def handler(req):
        return httpx.Response(302, headers={"location": "http://internal.test/admin"})
    with pytest.raises(JobFetchError, match="non-public"):
        fetch_public_page("http://pub.test/job", S,
                          resolver=_resolver({"pub.test": ["93.184.216.34"], "internal.test": ["10.0.0.9"]}),
                          transport=httpx.MockTransport(handler))


def test_redirect_loop_limited():
    def handler(req):
        return httpx.Response(302, headers={"location": "http://pub.test/again"})
    with pytest.raises(JobFetchError, match="redirect"):
        fetch_public_page("http://pub.test/a", S, resolver=_resolver({"pub.test": ["93.184.216.34"]}),
                          transport=httpx.MockTransport(handler))


def test_request_is_pinned_to_validated_ip_with_host_header():
    seen = {}

    def handler(req):
        seen["url"], seen["host"] = str(req.url), req.headers["host"]
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>hi</p>")
    r = fetch_public_page("https://pub.test/job?id=1", S, resolver=_resolver({"pub.test": ["93.184.216.34"]}),
                          transport=httpx.MockTransport(handler))
    assert seen["url"].startswith("https://93.184.216.34/job?id=1")
    assert seen["host"] == "pub.test" and r.body == "<p>hi</p>"


def test_oversize_and_wrong_type_rejected():
    big = httpx.MockTransport(lambda r: httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * 5000))
    res = _resolver({"pub.test": ["93.184.216.34"]})
    with pytest.raises(JobFetchError, match="too large"):
        fetch_public_page("http://pub.test/", S, resolver=res, transport=big)
    pdf = httpx.MockTransport(lambda r: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"x"))
    with pytest.raises(JobFetchError, match="HTML or text"):
        fetch_public_page("http://pub.test/", S, resolver=res, transport=pdf)


def test_non_200_rejected():
    t = httpx.MockTransport(lambda r: httpx.Response(403))
    with pytest.raises(JobFetchError, match="403"):
        fetch_public_page("http://pub.test/", S, resolver=_resolver({"pub.test": ["93.184.216.34"]}), transport=t)
