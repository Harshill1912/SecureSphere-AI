"""Logging configuration for production"""
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from config import get_settings

settings = get_settings()


def setup_logging():
    """Configure application logging"""
    # Create logs directory if it doesn't exist
    log_file_path = Path(settings.LOG_FILE)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=settings.LOG_FORMAT,
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler with rotation
            RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


# Initialize logger
logger = setup_logging()
