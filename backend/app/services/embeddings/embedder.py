"""Retrieval rankers. Scores are used only to order candidates / gate weak matches;
they are never reported as proficiency.
"""
import math
import re
from collections import Counter
from typing import Protocol

STOP = set(
    """a an and are as at be by for from has have in is it of on or that the to with will you your we our
    their this these those who can able ability strong good excellent knowledge experience experienced
    years year proficiency proficient skills skill working work familiarity understanding required
    preferred plus bonus must should including using use etc more least minimum solid proven demonstrated""".split()
)
_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#./-]*")


def tokenize(text: str) -> list[str]:
    toks = []
    for t in _TOKEN.findall(text.lower()):
        t = t.strip(".-/")
        if len(t) > 3 and t.endswith("ing"):
            t = t[:-3]
        elif len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        if t and t not in STOP:
            toks.append(t)
    return toks


class Ranker(Protocol):
    name: str
    min_related: float  # below this the best match is considered irrelevant

    def fit(self, texts: list[str]) -> None: ...
    def score(self, query: str) -> list[float]: ...


class LexicalRanker:
    """Idf-weighted query-term coverage in [0, 1]. No model download required."""

    name = "lexical"
    min_related = 0.34

    def __init__(self) -> None:
        self._docs: list[set[str]] = []
        self._idf: dict[str, float] = {}

    def fit(self, texts: list[str]) -> None:
        self._docs = [set(tokenize(t)) for t in texts]
        df: Counter[str] = Counter()
        for d in self._docs:
            df.update(d)
        n = max(len(self._docs), 1)
        self._idf = {t: math.log(1 + n / c) for t, c in df.items()}

    def score(self, query: str) -> list[float]:
        q = set(tokenize(query))
        if not q:
            return [0.0] * len(self._docs)
        default = math.log(1 + max(len(self._docs), 1))
        weights = {t: self._idf.get(t, default) for t in q}
        total = sum(weights.values())
        return [sum(w for t, w in weights.items() if t in d) / total for d in self._docs]


class SentenceTransformerRanker:
    name = "sentence-transformers"
    min_related = 0.30  # cosine; calibrate with the evaluation script before relying on it

    _models: dict[str, object] = {}

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._emb = None

    def _model(self):
        if self.model_name not in self._models:  # loaded once per process
            from sentence_transformers import SentenceTransformer

            self._models[self.model_name] = SentenceTransformer(self.model_name)
        return self._models[self.model_name]

    def fit(self, texts: list[str]) -> None:
        self._emb = self._model().encode(texts, normalize_embeddings=True) if texts else []

    def score(self, query: str) -> list[float]:
        if self._emb is None or len(self._emb) == 0:
            return []
        q = self._model().encode([query], normalize_embeddings=True)[0]
        return [float(v) for v in self._emb @ q]


def make_ranker(backend: str, model_name: str) -> tuple[Ranker, str | None]:
    """Returns (ranker, warning). Falls back to lexical if the ML backend is unusable."""
    if backend == "sentence-transformers":
        try:
            import sentence_transformers  # noqa: F401

            return SentenceTransformerRanker(model_name), None
        except ImportError:
            return LexicalRanker(), (
                "sentence-transformers is not installed; used lexical retrieval instead."
            )
    return LexicalRanker(), None
