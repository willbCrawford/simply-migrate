import logging
from typing import Any


class ContextLogger:
    """Wraps a standard logger and injects structured context into every log call"""

    def __init__(self, logger: logging.Logger, context: dict[str, Any] = None):
        self._logger = logger
        self._context = context or {}

    def _log(self, level: int, message: str, **kwargs):
        extra = {**self._context, **kwargs}
        self._logger.log(level, message, extra=extra, stacklevel=3)

    def with_context(self, **kwargs) -> "ContextLogger":
        """Return a new logger with additional context merged in"""
        return ContextLogger(self._logger, {**self._context, **kwargs})

    def debug(self, message: str, **kwargs): self._log(logging.DEBUG, message, **kwargs)
    def info(self, message: str, **kwargs): self._log(logging.INFO, message, **kwargs)
    def warning(self, message: str, **kwargs): self._log(logging.WARNING, message, **kwargs)
    def error(self, message: str, **kwargs): self._log(logging.ERROR, message, **kwargs)
    def critical(self, message: str, **kwargs): self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        extra = {**self._context, **kwargs}
        self._logger.exception(message, extra=extra)

    @property
    def context(self):
        return self._context


def get_logger(name: str, **context) -> ContextLogger:
    if not name.startswith("app"):
        name = f"app.{name}"
    return ContextLogger(logging.getLogger(name), context)