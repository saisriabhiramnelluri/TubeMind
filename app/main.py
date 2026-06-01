"""FastAPI application entry point with startup/shutdown lifecycle."""

import numpy as np
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import get_settings
from app.middleware.logger import setup_logging, log_separator
from app.middleware.error_handler import (
    value_error_handler,
    runtime_error_handler,
    generic_error_handler,
)
from app.db.database import init_db, close_db, get_session_factory
from app.db.models import get_all_chunks_with_embeddings
from app.embeddings.embedder import get_embedder
from app.vectorstore.faiss_manager import get_faiss_manager

from app.api import health, ingest, query, query_stream, videos

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # -- Startup -------------------------------------------------------
    setup_logging()
    logger.info("Application startup initiated")
    log_separator(logger)

    # Database
    logger.info("Initializing database tables")
    await init_db()

    # Embedding model
    logger.info("Loading embedding model into memory")
    embedder = get_embedder()
    dim = embedder.dimension
    logger.info("Embedding model ready  [dimension=%d]", dim)
    log_separator(logger)

    # FAISS vector index
    logger.info("Creating FAISS vector index  [dimension=%d]", dim)
    faiss_mgr = get_faiss_manager(dimension=dim)

    logger.info("Rebuilding FAISS index from persisted embeddings in PostgreSQL")
    factory = get_session_factory()
    async with factory() as session:
        chunks = await get_all_chunks_with_embeddings(session)

        if chunks:
            embeddings = np.array(
                [np.frombuffer(c.embedding, dtype=np.float32) for c in chunks],
                dtype=np.float32,
            )
            metadata_list = [
                {
                    "video_id": c.video_id,
                    "chunk_index": c.chunk_index,
                    "text": c.text,
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                }
                for c in chunks
            ]
            faiss_mgr.rebuild_from_data(embeddings, metadata_list)
            logger.info("FAISS index rebuilt successfully  [vectors=%d]", len(chunks))
        else:
            logger.info("No persisted embeddings found -- FAISS index is empty")

    log_separator(logger)
    logger.info("Application startup complete -- ready to accept requests")

    yield

    # -- Shutdown ------------------------------------------------------
    logger.info("Application shutdown initiated")
    await close_db()
    logger.info("Application shutdown complete")


# ── Create FastAPI App ──
app = FastAPI(
    title="TubeMind",
    description="AI-powered understanding for every YouTube video. Transforms videos into searchable, interactive conversations using Retrieval-Augmented Generation (RAG).",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──
_settings = get_settings()
_origins = ["*"]
if _settings.frontend_url:
    _origins = [
        _settings.frontend_url,
        "http://localhost:8000",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ──
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(RuntimeError, runtime_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# ── API Routes ──
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(query_stream.router, prefix="/api", tags=["Query"])
app.include_router(videos.router, prefix="/api", tags=["Videos"])

# ── Frontend Static Files ──
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend HTML."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))
