from simply_migrate.logging.logger import ContextLogger
from simply_migrate.logging.config import configure_logging, LogLevel, AppEnvironment, ConsoleFormat


class LoggingContainer:
    def __init__(self, logger: ContextLogger):
        self._logger = logger

    def get_logger(self, **context) -> ContextLogger:
        return self._logger.with_context(**context) if context else self._logger

    @classmethod
    def create(
        cls,
        log_level: LogLevel = LogLevel.INFO,
        environment: AppEnvironment = AppEnvironment.DEVELOPMENT,
        log_file: bool = True,
        service: str = "simply-migrate",
        console_format: ConsoleFormat = ConsoleFormat.JSON,
        silent_mode: bool = False
    ) -> "LoggingContainer":
        root_logger = configure_logging(
            log_level=log_level,
            environment=environment,
            log_file=log_file,
            service=service,
            console_format=console_format,
            silent_mode=silent_mode
        )
        return cls(root_logger)