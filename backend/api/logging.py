from __future__ import annotations

import logging

def get_logger(name: str | None = None) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name or __name__)


def log_token_source(
    logger: logging.Logger,
    label: str,
    token: str | None,
    level_success: int = logging.DEBUG,
    level_failure: int = logging.DEBUG,
) -> None:
    """
    Structured helper for reporting token sourcing decisions.

    Avoid logging the token value; only the source label is emitted.
    """
    if token:
        logger.log(level_success, "Token provider %s supplied credentials", label)
    else:
        logger.log(level_failure, "Token provider %s produced no credentials", label)
