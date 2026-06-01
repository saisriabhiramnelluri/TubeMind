"""Structured logging configuration with clean, professional terminal output."""

import logging
import sys


# ---------------------------------------------------------------------------
# Custom formatter — each log line prints as:
#   [HH:MM:SS] INFO  | server         | message text here
# ---------------------------------------------------------------------------

class CleanFormatter(logging.Formatter):
    """Professional terminal output with aligned, pipe-delimited columns."""

    LEVEL_TAGS = {
        logging.DEBUG:    "DEBUG",
        logging.INFO:     "INFO ",
        logging.WARNING:  "WARN ",
        logging.ERROR:    "ERROR",
        logging.CRITICAL: "FATAL",
    }

    COMPONENT_MAP = {
        "app.main":                          "server",
        "app.config":                        "config",
        "app.db.database":                   "database",
        "app.db.models":                     "database",
        "app.embeddings.embedder":           "embedder",
        "app.vectorstore.faiss_manager":     "vector-store",
        "app.vectorstore.retriever":         "retriever",
        "app.rag.pipeline":                  "rag-pipeline",
        "app.rag.response_generator":        "gemini",
        "app.rag.prompt_builder":            "prompt",
        "app.ingestion.youtube_loader":      "youtube",
        "app.ingestion.chunker":             "chunker",
        "app.ingestion.transcript_cleaner":  "transcript",
        "app.ingestion.metadata_extractor":  "metadata",
        "app.api.ingest":                    "api-ingest",
        "app.api.query":                     "api-query",
        "app.api.videos":                    "api-videos",
        "app.api.health":                    "api-health",
        "app.middleware.error_handler":       "error-handler",
    }

    def format(self, record):
        timestamp = self.formatTime(record, "%H:%M:%S")
        tag = self.LEVEL_TAGS.get(record.levelno, record.levelname)
        component = self.COMPONENT_MAP.get(record.name, record.name.split(".")[-1])
        message = record.getMessage()
        return f"  [{timestamp}] {tag} | {component:<16} | {message}"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

_SEPARATOR = "  " + "-" * 62

def log_separator(logger: logging.Logger):
    """Print a horizontal rule to visually separate startup phases."""
    logger.info(_SEPARATOR.strip())


def setup_logging(level: str = "INFO"):
    """Configure structured logging for the entire application.

    - Attaches a single console handler with the CleanFormatter.
    - Suppresses noisy output from third-party libraries so only
      application-level messages appear in the terminal.
    """
    formatter = CleanFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers on reload
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
    else:
        root_logger.handlers = [console_handler]

    # Suppress noisy third-party libraries
    noisy_libraries = [
        "httpx", "httpcore", "urllib3",
        "sentence_transformers", "faiss",
        "watchfiles", "multipart",
        "uvicorn.access",
    ]
    for lib in noisy_libraries:
        logging.getLogger(lib).setLevel(logging.WARNING)
