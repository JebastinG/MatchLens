import json
import re

import httpx


class LLMUnavailable(Exception):
    pass


class OllamaClient:
    """Minimal Ollama client. Only the backend talks to Ollama (never the browser)."""

    def __init__(self, base_url: str, model: str, timeout: float = 180.0, num_ctx: int = 4096,
                 transport: httpx.BaseTransport | None = None):
        self.base_url, self.model, self.timeout, self.num_ctx = base_url.rstrip("/"), model, timeout, num_ctx
        self._transport = transport

    def _client(self, timeout: float) -> httpx.Client:
        return httpx.Client(timeout=timeout, transport=self._transport, trust_env=False)

    def installed_models(self) -> list[str]:
        try:
            with self._client(5.0) as c:
                r = c.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                return [m["name"] for m in r.json().get("models", [])]
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise LLMUnavailable("Ollama is not reachable.") from exc

    def check(self) -> tuple[bool, str | None, list[str]]:
        try:
            models = self.installed_models()
        except LLMUnavailable as exc:
            return False, str(exc), []
        names = {m for m in models} | {m.split(":")[0] for m in models if m.endswith(":latest")}
        if self.model not in names:
            return False, f"Model '{self.model}' is not installed (run: ollama pull {self.model}).", models
        return True, None, models

    def chat_json(self, system: str, user: str, schema: dict, num_predict: int = 600) -> object:
        body = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0, "num_ctx": self.num_ctx, "num_predict": num_predict},
        }
        try:
            with self._client(self.timeout) as c:
                r = c.post(f"{self.base_url}/api/chat", json=body)
                r.raise_for_status()
                content = r.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMUnavailable("The local model request failed.") from exc
        return parse_json(content)


def parse_json(content: str) -> object:
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    try:
        return json.loads(content)
    except ValueError:
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                pass
    return None
