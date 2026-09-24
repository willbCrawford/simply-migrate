import logging
import logging.config
from enum import Enum
from simply_migrate.logging.formatters import JSONFormatter, PlainTextFormatter
from simply_migrate.logging.logger import ContextLogger, get_logger

from logging.handlers import RotatingFileHandler

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class ConsoleFormat(str, Enum):
    JSON = "json"
    PLAIN = "plain"


def configure_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_file: bool = True,
    service: str = "simply-migrate",
    environment: str = AppEnvironment.DEVELOPMENT,
    console_format: ConsoleFormat = ConsoleFormat.JSON,
    silent_mode: bool = False,
) -> ContextLogger:
    if silent_mode and not log_file:
        raise ValueError(
            "silent_mode=True requires log_file=True. "
            "Without a log file, silent mode would discard all output."
        )

    import os
    os.makedirs("logs", exist_ok=True)

    json_formatter = JSONFormatter(service=service, environment=environment)
    plain_formatter = PlainTextFormatter()

    console_formatter = plain_formatter if console_format == ConsoleFormat.PLAIN else json_formatter

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    handlers = []

    if not silent_mode:
        console_formatter = plain_formatter if console_format == ConsoleFormat.PLAIN else json_formatter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    if log_file:
        file_handler = RotatingFileHandler(
            "logs/simply_migrate.log",
            maxBytes=10_485_760,
            backupCount=5,
        )
        file_handler.setFormatter(json_formatter)
        handlers.append(file_handler)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level.value)
    app_logger.handlers = []  # clear any existing handlers
    app_logger.propagate = False

    for handler in handlers:
        app_logger.addHandler(handler)

    return get_logger("app", environment=environment)