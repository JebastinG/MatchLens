import io

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import Settings
from app.db.session import get_engine
from app.main import create_app
from app.models import Base
from app.workers.pipeline import Deps

RESUME_LINES = [
    "Alex Example",
    "Backend Engineer",
    "Skills: Python, SQL, Docker, Git, Linux, REST API",
    "Experience",
    "- Built a REST API in Python with FastAPI serving 40 internal users and wrote pytest suites for it.",
    "- Designed PostgreSQL schemas and optimized slow SQL queries for a reporting service.",
    "- Containerized services with Docker and automated deployments with GitHub Actions.",
    "- Led a team of 3 engineers during a migration project and ran weekly planning sessions.",
]

JOB_TEXT = """Senior Backend Engineer at ExampleCo

About us
We build tools for logistics teams.

Requirements
- 3+ years of experience with Python
- Experience with PostgreSQL or MySQL
- Experience with Kubernetes
- Familiarity with React
- Strong written communication skills

Nice to have
- Experience with AWS
"""


def make_pdf(lines: list[str] = RESUME_LINES, pages: int = 1) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for _ in range(pages):
        y = 740
        for ln in lines:
            c.drawString(50, y, ln.replace("- ", "• ") if ln.startswith("- ") else ln)
            y -= 18
        c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite:///{tmp_path/'t.db'}", data_dir=tmp_path / "data",
                    run_worker=False, llm_enabled=False, rate_limit_per_minute=0)


@pytest.fixture
def make_client(settings):
    clients = []

    def _make(deps: Deps | None = None, **kw):
        app = create_app(settings, deps or Deps(settings), engine_url=settings.database_url, **kw)
        cm = TestClient(app)
        client = cm.__enter__()
        Base.metadata.create_all(get_engine())
        clients.append(cm)
        return client

    yield _make
    for cm in clients:
        cm.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


def submit(client, pdf: bytes | None = None, **form):
    data = {"job_mode": "paste", "job_description": JOB_TEXT}
    data.update(form)
    files = {"resume": ("resume.pdf", pdf if pdf is not None else make_pdf(), "application/pdf")}
    return client.post("/api/v1/analyses", data=data, files=files)


def run_and_get(client, resp):
    assert resp.status_code == 202, resp.text
    aid = resp.json()["id"]
    assert client.app.state.worker.process_one() is True
    return aid, client.get(f"/api/v1/analyses/{aid}/results")
