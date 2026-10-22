"""Small, explicit skill lexicon used for deterministic matching.

This is intentionally limited. Requirements that mention no lexicon term are handled
by retrieval + (optional) LLM and are never auto-marked "supported" by rules alone.
"""
import re
from functools import lru_cache

SKILLS: dict[str, list[str]] = {
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript"],
    "c++": ["c++"],
    "c#": ["c#"],
    "golang": ["golang"],
    "rust": ["rust"],
    "sql": ["sql"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "react": ["react", "react.js", "reactjs"],
    "angular": ["angular"],
    "vue": ["vue", "vue.js"],
    "node.js": ["node.js", "nodejs", "node"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "spring": ["spring", "spring boot"],
    "rest api": ["rest api", "rest apis", "restful", "rest"],
    "graphql": ["graphql"],
    "docker": ["docker", "containers", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "terraform": ["terraform"],
    "linux": ["linux"],
    "git": ["git", "github", "gitlab"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration", "github actions", "jenkins"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning"],
    "nlp": ["nlp", "natural language processing"],
    "pytorch": ["pytorch"],
    "tensorflow": ["tensorflow"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "llm": ["llm", "llms", "large language model", "large language models"],
    "data analysis": ["data analysis", "data analytics"],
    "testing": ["unit testing", "pytest", "jest", "test automation", "integration testing"],
    "agile": ["agile", "scrum", "kanban"],
    "microservices": ["microservices", "microservice"],
    "security": ["owasp", "application security"],
}

RELATED: dict[str, set[str]] = {
    "postgresql": {"sql", "mysql"},
    "mysql": {"sql", "postgresql"},
    "sql": {"postgresql", "mysql"},
    "react": {"javascript", "typescript", "angular", "vue"},
    "angular": {"javascript", "typescript", "react", "vue"},
    "vue": {"javascript", "typescript", "react", "angular"},
    "typescript": {"javascript"},
    "javascript": {"typescript", "node.js"},
    "node.js": {"javascript", "typescript"},
    "fastapi": {"flask", "django", "python"},
    "flask": {"fastapi", "django", "python"},
    "django": {"flask", "fastapi", "python"},
    "kubernetes": {"docker"},
    "docker": {"kubernetes"},
    "aws": {"azure", "gcp"},
    "azure": {"aws", "gcp"},
    "gcp": {"aws", "azure"},
    "pytorch": {"tensorflow", "machine learning", "deep learning"},
    "tensorflow": {"pytorch", "machine learning", "deep learning"},
    "machine learning": {"deep learning", "scikit-learn", "pytorch", "tensorflow"},
    "deep learning": {"pytorch", "tensorflow", "machine learning"},
    "nlp": {"machine learning", "llm"},
    "llm": {"nlp", "machine learning"},
    "ci/cd": {"git", "docker"},
    "rest api": {"fastapi", "flask", "django", "graphql"},
    "java": {"spring"},
    "spring": {"java"},
    "pandas": {"numpy", "data analysis"},
    "data analysis": {"pandas", "sql"},
}

_FIRST = r"(?<![\w+#./-])"
_LAST = r"(?![\w+#]|\.\w|-\w)"


@lru_cache
def _patterns() -> list[tuple[str, re.Pattern]]:
    out = []
    for canon, aliases in SKILLS.items():
        alts = "|".join(re.escape(a) for a in sorted(set(aliases + [canon]), key=len, reverse=True))
        out.append((canon, re.compile(f"{_FIRST}(?:{alts}){_LAST}", re.IGNORECASE)))
    return out


def find_terms(text: str) -> list[str]:
    return [canon for canon, pat in _patterns() if pat.search(text)]


def is_skill_listing(text: str) -> bool:
    """Heuristic: a line that just lists tools (claim without demonstrated use)."""
    terms = find_terms(text)
    seps = text.count(",") + text.count("|") + text.count(";") + text.count("•")
    head = text[:30].lower()
    labelled = head.startswith(("skills", "technologies", "tools", "languages", "technical"))
    return labelled or (len(terms) >= 4 and seps >= 3)
