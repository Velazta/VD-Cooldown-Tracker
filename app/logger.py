"""Centralized Logging Module for Violence District Cooldown Tracker.

Follows official Python logging standards:
https://docs.python.org/3/library/logging.html

Provides structured logging with console output and rotating file storage,
ensuring clean debugging and production-grade event auditing.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

# Root logger identifier for the application
APP_LOGGER_NAME = "VDTracker"

# Formats
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    debug_mode: bool = False,
    log_file: Optional[Union[str, Path]] = None,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> logging.Logger:
    """Configure the application root logger with console and rotating file handlers.

    Args:
        debug_mode: If True, sets console log level to DEBUG; otherwise INFO.
        log_file: Path to the log file. Defaults to 'logs/app.log' relative to project root.
        max_bytes: Maximum file size before rotation.
        backup_count: Number of rotated log files to retain.

    Returns:
        The configured top-level logging.Logger instance.
    """
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)  # Capture everything at logger level; filter at handlers

    # Clear existing handlers if reconfiguring to avoid duplicate logs
    if logger.hasHandlers():
        for handler in list(logger.handlers):
            handler.close()
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # 1. Console Handler (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (RotatingFileHandler)
    if log_file is None:
        project_root = Path(__file__).resolve().parent.parent
        log_file = project_root / "logs" / "app.log"
    else:
        log_file = Path(log_file)

    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Always write detailed DEBUG logs to disk
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as exc:
        logger.warning("Could not initialize file log handler at %s: %s", log_file, exc)

    logger.debug(
        "Logging initialized. Mode: %s | Log File: %s",
        "DEBUG" if debug_mode else "INFO",
        log_file,
    )
    return logger


def get_logger(child_name: Optional[str] = None) -> logging.Logger:
    """Retrieve an application logger or child logger.

    Args:
        child_name: Optional sub-module name (e.g. 'capture', 'database', 'gui').

    Returns:
        logging.Logger: The requested logger instance.
    """
    if not child_name:
        return logging.getLogger(APP_LOGGER_NAME)
    return logging.getLogger(f"{APP_LOGGER_NAME}.{child_name}")
