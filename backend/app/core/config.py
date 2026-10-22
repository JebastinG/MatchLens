from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (secrets come from the environment / .env, never from code)
    database_url: str = "postgresql+psycopg://matchlens_app:change-me@127.0.0.1:5432/matchlens"
    migration_database_url: str | None = None  # owner role used by Alembic only

    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    data_dir: Path = Path("data")

    # Uploads
    max_upload_mb: int = 5
    max_pdf_pages: int = 30
    min_resume_chars: int = 200

    # Ollama / LLM
    llm_enabled: bool = True
    require_llm: bool = False  # True -> POST /analyses returns 503 when Ollama is unavailable
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_s: float = 180.0
    ollama_num_ctx: int = 4096
    llm_max_requirements: int = 20

    # Embeddings: "lexical" (no model download) or "sentence-transformers"
    embedding_backend: str = "lexical"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # GitHub (optional token only raises the API rate limit)
    github_token: str | None = None
    github_max_repos: int = 3
    github_max_files_per_repo: int = 12
    github_max_file_bytes: int = 100_000

    # Job URL fetching
    job_fetch_timeout_s: float = 10.0
    job_max_bytes: int = 1_500_000
    job_max_redirects: int = 3
    max_requirements: int = 25

    rate_limit_per_minute: int = 10
    run_worker: bool = True
    worker_poll_interval_s: float = 1.0
    worker_max_attempts: int = 2

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
