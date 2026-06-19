"""Logging setup for FootyOracle."""

import logging
import logging.handlers
import threading
from typing import Optional
from pathlib import Path
from app.core.config import get_settings

# Thread-safe logger initialization
_logger_lock = threading.Lock()
_initialized_loggers = set()


def setup_logger(name: str) -> logging.Logger:
    """Configure logger instance with file and console handlers."""
    
    global _initialized_loggers
    
    with _logger_lock:
        # Skip if already initialized
        if name in _initialized_loggers:
            return logging.getLogger(name)
        
        settings = get_settings()
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        # Avoid duplicate handlers
        if logger.handlers:
            _initialized_loggers.add(name)
            return logger
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler with rotation
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / f"{name}.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")
        
        _initialized_loggers.add(name)
        return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create logger by name with automatic setup."""
    logger = logging.getLogger(name)
    
    # Initialize if not already initialized
    if name not in _initialized_loggers:
        setup_logger(name)
    
    return logger
