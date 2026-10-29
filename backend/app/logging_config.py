"""Rotating local activity and request logs with safe default retention."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.app.config import DATA_DIR


def _logger(channel: str) -> logging.Logger:
    logger = logging.getLogger(channel)
    if logger.handlers:
        return logger
    try:
        log_dir = DATA_DIR / "logs"
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


def clear_log_history() -> bool:
    """Remove rotated local logs and start fresh files for each configured log channel."""
    cleared = True
    for channel in ("activity", "requests"):
        logger = logging.getLogger(channel)
        for handler in logger.handlers:
            if not isinstance(handler, RotatingFileHandler):
                continue
            log_path = Path(handler.baseFilename)
            handler.acquire()
            try:
                handler.doRollover()
                for previous in log_path.parent.glob(f"{log_path.name}.*"):
                    previous.unlink(missing_ok=True)
            except OSError:
                cleared = False
            finally:
                handler.release()
    return cleared


activity = _logger("activity")
requests = _logger("requests")
