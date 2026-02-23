"""
MGB Dash 2026 — Shared Logging Configuration

Configures Python logging with rotating file handler and console output.
All modules use this for consistent log format and auto-persisted logs.

Log files:  <repo>/logs/<name>.log  (10 MB per file, 5 backups)

Usage:
    from common.python.log_setup import setup_logging
    logger = setup_logging("GPS")
    logger.critical("GPS display starting...")
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logging(name: str, log_dir: str = None) -> logging.Logger:
    """
    Configure and return a named logger with rotating file + console handlers.

    Args:
        name:     Module name (e.g., "GPS", "DASH", "can-monitor")
        log_dir:  Override log directory (default: <repo>/logs/)

    Returns:
        Configured logging.Logger instance
    """
    if log_dir is None:
        log_dir = LOG_DIR
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(f"mgb.{name.lower()}")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Rotating file handler — 10 MB per file, 5 backups
    log_file = os.path.join(log_dir, f"{name.lower()}.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
