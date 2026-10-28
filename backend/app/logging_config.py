"""Rotating local activity and request logs with safe default retention."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _logger(channel: str) -> logging.Logger:
    logger = logging.getLogger(channel)
    if logger.handlers:
        return logger
    try:
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / f"{channel}.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger


activity = _logger("activity")
requests = _logger("requests")
