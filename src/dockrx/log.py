"""Structured logging for DockRx.

Usage:
    from dockrx.log import logger
    logger.debug("Parsing Dockerfile: %s", path)
    logger.info("Found %d findings", len(findings))
    logger.warning("No .dockerignore found")
    logger.error("Failed to parse: %s", exc_info=True)

Log level is controlled via:
- Environment variable: DOCKRX_LOG_LEVEL (default: WARNING)
- pyproject.toml: [tool.dockrx] log-level = "DEBUG"
"""

from __future__ import annotations

import logging
import os
from typing import Final

LOGGER_NAME: Final[str] = "dockrx"

# Map string level names to logging constants
_LOG_LEVELS: Final[dict[str, int]] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _resolve_log_level() -> int:
    """Determine log level from environment or default to WARNING."""
    env_level = os.environ.get("DOCKRX_LOG_LEVEL", "").upper()
    if env_level in _LOG_LEVELS:
        return _LOG_LEVELS[env_level]

    # Try reading from a config file — lazy import to avoid circular deps
    try:
        from dockrx.config import load_config

        cfg = load_config()
        cfg_level = (cfg.get("log-level") or "").upper()
        if cfg_level in _LOG_LEVELS:
            return _LOG_LEVELS[cfg_level]
    except Exception:
        pass  # Best-effort; fall through to default.

    return logging.WARNING


def _setup_logger() -> logging.Logger:
    """Create and configure the DockRx logger."""
    level = _resolve_log_level()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated setup
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger: logging.Logger = _setup_logger()
"""Module-level logger for all DockRx components."""
