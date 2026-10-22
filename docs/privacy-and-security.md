# Privacy and security

## Data flow
Resume and job text are processed on your machine. The default (and only built-in) LLM path is local Ollama; nothing is sent to an external AI provider. Outbound network use: (1) the job URL you supply, via the guarded fetcher; (2) `api.github.com` if you supply a GitHub URL; (3) one-time downloads of dependencies and model weights by you (pip, npm, `ollama pull`, Hugging Face). Model weights/dependencies are stored locally.

## Threat model and controls
| Threat | Control | Verified by |
|---|---|---|
| SSRF via job URL | http/https only; ports 80/443; no credentials in URL; hostname resolved and **every** address must be globally routable (blocks loopback, RFC1918, link-local/metadata 169.254.x, CGNAT, multicast, IPv4-mapped IPv6); each redirect re-validated (max 3); request pinned to the validated IP with Host/SNI preserved (anti DNS-rebinding); 10 s timeout; 1.5 MB cap; HTML/text only; no proxy env (`trust_env=False`) | `tests/unit/test_ssrf_and_fetch.py`, `tests/security` (mocked DNS/transport) |
| Malicious HTML | parsed with BeautifulSoup only; scripts removed, never executed | unit test |
| Malicious PDF / upload abuse | size cap while streaming, `%PDF-` signature, PyMuPDF open, page cap, encrypted/empty/scanned rejection, stored under a server-generated name, deleted after processing | integration tests |
| Prompt injection (resume, job, repo text) | text only inside delimited data tags, delimiter strings stripped, system prompt says data is untrusted, output limited by JSON schema, **and** all output validated against sources; rules cap model upgrades | security tests with scripted fake LLM; **not** tested against a real model |
| Fabricated evidence | quotes must be substrings of retrieved text; unknown ids dropped; GitHub paths/lines come only from the API | unit + integration |
| Malicious repo content | read as text via API; never cloned or executed; allow-listed extensions, size/file/repo caps | unit tests |
| Cross-origin abuse | CORS limited to configured origins; no credentials/cookies | security test |
| Secrets | env vars / `.env` (git-ignored); least-privilege DB role | PG test |
| Log leakage | no content logged; generic error bodies; httpx URL logging off | review |
| Abuse/DoS | per-IP rate limit (in-memory), upload/page/requirement caps, single worker | tests |
| Deletion races | cascade deletes; worker checkpoints; FK-guarded final write | integration test |

## Residual risks and gaps
- **No authentication or per-user isolation.** Anyone who can reach the API can read/delete any analysis by id. Bind to 127.0.0.1 (default) and do not expose it. Ids are random 128-bit but are bearer secrets.
- Rate limiter is per-process memory and keyed on client IP.
- Pinned-IP fetch relies on httpx/httpcore `sni_hostname` behaviour (mocked in tests; not exercised against real TLS sites here).
- Not covered: OCR-based attacks, PDF parser zero-days (keep PyMuPDF updated), local malware, disk encryption, DB backups.
- Job pages and GitHub learn that you made a request from your IP.
- Dependency/vulnerability scanning (pip-audit, npm audit) was **not run**.
- Guidance consulted: Ollama structured-output docs; OWASP SSRF Prevention Cheat Sheet (https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html — located via search, not studied line-by-line).
