"""
Logger - Application logging configuration.

Sets up file and console logging with rotation.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from PyQt5.QtCore import QObject, pyqtSignal

from src.config import config


def setup_logging(
    level: str | None = None,
    log_file: Path | None = None,
) -> logging.Logger:
    """
    Set up application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        
    Returns:
        Root logger instance
    """
    log_level = getattr(logging, level or config.logging.level.upper(), logging.INFO)
    log_path = log_file or config.logging.file_path
    
    # Create logs directory
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Log format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class QtLogEmitter(QObject):
    """Qt object that relays log records via signal across threads."""

    log_message = pyqtSignal(str, str)  # level, formatted message

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)


class GUILogHandler(logging.Handler):
    """Custom log handler that forwards records through Qt signals."""

    def __init__(self, emitter: QtLogEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.emitter.log_message.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)
