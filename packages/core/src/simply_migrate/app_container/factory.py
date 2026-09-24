from simply_migrate.logging.container import LoggingContainer
from simply_migrate.logging.config import LogLevel, AppEnvironment, ConsoleFormat


class AppContainer:
    def __init__(self, logging: LoggingContainer):
        self.logging = logging

    @classmethod
    def create(
        cls,
        log_level: LogLevel = LogLevel.INFO,
        environment: AppEnvironment = AppEnvironment.DEVELOPMENT,
        log_file: bool = True,
        service: str = "simply-migrate",
        console_format: ConsoleFormat = ConsoleFormat.JSON,
        silent_mode: bool = False
    ) -> "AppContainer":
        logging = LoggingContainer.create(
            log_level=log_level,
            environment=environment,
            log_file=log_file,
            service=service,
            console_format=console_format,
            silent_mode=silent_mode
        )
        return cls(logging=logging)

