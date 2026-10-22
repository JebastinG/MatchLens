import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.db.session import init_engine
from app.workers.pipeline import Deps, Worker, default_deps


def create_app(settings: Settings | None = None, deps: Deps | None = None,
               resolver=None, http_transport=None, engine_url: str | None = None) -> FastAPI:
    st = settings or get_settings()
    deps = deps or default_deps(st)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # do not log fetched URLs
    # Request bodies / resume text are never logged.

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_engine(engine_url or st.database_url)
        st.upload_dir.mkdir(parents=True, exist_ok=True)
        worker = Worker(deps)
        if st.run_worker:
            worker.start()
        app.state.worker = worker
        yield
        worker.stop()

    app = FastAPI(title="MatchLens API", version="0.1.0", lifespan=lifespan)
    app.state.settings, app.state.deps = st, deps
    app.state.resolver, app.state.http_transport = resolver, http_transport
    app.add_middleware(
        CORSMiddleware, allow_origins=st.cors_origin_list, allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"], allow_credentials=False)
    install_error_handlers(app)
    app.include_router(router)
    return app


def app_factory() -> FastAPI:  # uvicorn app.main:app_factory --factory
    return create_app()
