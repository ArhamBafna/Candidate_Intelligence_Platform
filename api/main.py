from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import structlog
from config.logging import setup_logging, is_polling_path
import time
import uuid

# Set up canonical structured logging
setup_logging()
logger = structlog.get_logger(__name__)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from config.settings import get_settings
from config.database import get_engine
from storage.db_models import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema on startup
    settings = get_settings()
    engine = get_engine(f"sqlite:///{settings.db_path}")
    init_db(engine)
    yield

app = FastAPI(
    title="Candidate Intelligence Platform API",
    description="API for managing candidates, timelines, and hybrid search.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def structlog_middleware(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Uvicorn access lines are suppressed, so this http_request event is
        # the only access-history record; emit it even when the request blows
        # up (PR #25 review: failed requests must keep path/status/duration).
        duration_ms = (time.perf_counter() - start_time) * 1000
        structlog.contextvars.bind_contextvars(duration_ms=round(duration_ms, 2))
        if not is_polling_path(request.url.path):
            logger.error(
                "http_request",
                http_method=request.method,
                path=request.url.path,
                status_code=500,
                duration_s=round(duration_ms / 1000, 2),
                request_failed=True,
            )
        raise
    duration_ms = (time.perf_counter() - start_time) * 1000
    structlog.contextvars.bind_contextvars(duration_ms=round(duration_ms, 2))
    if not is_polling_path(request.url.path):
        logger.info(
            "http_request",
            http_method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_s=round(duration_ms / 1000, 2),
        )
    return response

from api.routes.candidates import router as candidates_router
from api.routes.search import router as search_router
from api.routes.logs import router as logs_router

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(candidates_router)
app.include_router(search_router)
app.include_router(logs_router)

