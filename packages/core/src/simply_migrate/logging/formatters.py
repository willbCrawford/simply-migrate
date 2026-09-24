import json
import logging
import traceback
from datetime import datetime, timezone


class PlainTextFormatter(logging.Formatter):
    """Human-readable formatter for CLI console output"""

    LEVEL_WIDTH = 8  # pad level names for alignment

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(self.LEVEL_WIDTH)
        message = record.getMessage()
        return f"{timestamp} {level} {message}"


class JSONFormatter(logging.Formatter):
    """Format log records as JSON objects for structured logging"""

    def __init__(self, service: str = "simply-migrate", environment: str = "development"):
        super().__init__()
        self.service = service
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service,
            "environment": self.environment,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # attach extra fields if provided
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        # attach exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # attach any extra fields passed via logger.info(..., extra={})
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName"
            }:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)  # default=str handles non-serializable types