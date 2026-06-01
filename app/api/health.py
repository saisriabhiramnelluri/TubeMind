"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_db
from app.vectorstore.faiss_manager import get_faiss_manager

router = APIRouter()


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db)):
    """Application health check with database and FAISS status."""
    try:
        # Check database
        result = await session.execute(text("SELECT COUNT(*) FROM videos"))
        videos_count = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM chunks"))
        chunks_count = result.scalar()

        # Check FAISS
        try:
            faiss_mgr = get_faiss_manager()
            vectors_count = faiss_mgr.total_vectors
        except Exception:
            vectors_count = 0

        return {
            "status": "healthy",
            "videos_count": videos_count,
            "chunks_count": chunks_count,
            "vectors_count": vectors_count,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
        }
