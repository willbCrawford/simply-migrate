from pathlib import Path
from typing import List, Tuple, Iterator

import pluggy
import logging

from simply_migrate.logging.logger import ContextLogger

migration_file_impl = pluggy.HookimplMarker("migration_file")

class LocalMigrationFilePlugin:
    def __init__(self):
        self.errors = []
        self.warnings = []

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def validate_directory(self, path: str, directory: str) -> Iterator[Path]:
        self.logger.info(f"validating directory {path + directory}")

        migration_path = Path(path + directory)

        if not migration_path.exists():
            self.errors.append(f"Migrations directory does not exist: {migration_path}")
            return iter([])

        if not migration_path.is_dir():
            self.errors.append(f"{migration_path} is not a directory")
            return iter([])

        sql_files = migration_path.glob("*.sql")

        if not sql_files:
            self.errors.append(f"No sql files found in {migration_path}")
            return iter([])

        return sql_files

    @migration_file_impl
    def get_files(self, path: str, directory: str, logger: ContextLogger) -> List[Tuple[str, str]]:
        self.logger = logger

        files = self.validate_directory(path, directory)

        migration_files = []

        for file in sorted(files):
            migration_files.append((file.name, file.read_text()))

        return migration_files

    @migration_file_impl
    def get_file(
        self,
        path: str,
        logger: ContextLogger,
    ) -> Tuple[str, str] | None:
        file_path = Path(path)

        if not file_path.exists():
            logger.error(f"Script not found: {file_path}")
            return None

        logger.info(f"Loaded script: {file_path.name}")
        return file_path.name, file_path.read_text()
