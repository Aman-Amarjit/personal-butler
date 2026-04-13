"""
Logging System - File and console output with structured logging.
"""

import logging
import logging.config
import logging.handlers
import os
import sys
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """
    Set up logging with file and console output.

    Args:
        log_dir: Directory for log files
        level: Logging level

    Returns:
        Configured logger
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "panda.log"),
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "panda_errors.log"),
                "maxBytes": 5 * 1024 * 1024,  # 5MB
                "backupCount": 3,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "panda": {
                "level": level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            }
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"]
        }
    }

    logging.config.dictConfig(log_config)
    return logging.getLogger("panda")


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the panda namespace.

    Args:
        name: Logger name (will be prefixed with 'panda.')

    Returns:
        Logger instance
    """
    return logging.getLogger(f"panda.{name}")
