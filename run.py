"""Development server entry point -- run: python run.py"""

import logging
import uvicorn
from app.config import get_settings

logger = logging.getLogger("app.main")


def main():
    settings = get_settings()

    logger.info("Starting development server on http://%s:%d", settings.host, settings.port)

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
