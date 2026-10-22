from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def make_engine(url: str) -> Engine:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(eng, "connect")
        def _fk(dbapi_conn, _):  # enforce FK cascades in SQLite (tests)
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return eng


def init_engine(url: str | None = None) -> Engine:
    global _engine, _factory
    _engine = make_engine(url or get_settings().database_url)
    _factory = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    return _engine or init_engine()


def session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _factory is not None
    return _factory


@contextmanager
def session_scope() -> Iterator[Session]:
    s = session_factory()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db() -> Iterator[Session]:
    s = session_factory()()
    try:
        yield s
    finally:
        s.close()
