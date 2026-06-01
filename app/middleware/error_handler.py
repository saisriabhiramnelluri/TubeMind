"""Global exception handlers for FastAPI."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError (validation, bad input)."""
    logger.warning("Validation error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "type": "validation_error"},
    )


async def runtime_error_handler(request: Request, exc: RuntimeError):
    """Handle RuntimeError (LLM failures, processing errors)."""
    logger.error("Processing error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": "processing_error"},
    )


async def generic_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.exception("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred.", "type": "internal_error"},
    )
