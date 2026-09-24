from pathlib import Path
from typing import List, Tuple

from simply_migrate.source.base import ScriptSource
from simply_migrate.logging.logger import ContextLogger


class LocalScriptSource(ScriptSource):

    def get_files(
        self,
        path: str,
        directory: str,
        logger: ContextLogger,
    ) -> List[Tuple[str, str]]:
        if directory == '':
            migrations_path = Path(path)
        else:
            migrations_path = Path(path) / directory

        logger.info(f"Found migrations directory: {migrations_path}")

        if not migrations_path.exists():
            raise FileNotFoundError(
                f"Directory not found: {migrations_path}"
            )
        if not migrations_path.is_dir():
            raise NotADirectoryError(
                f"{migrations_path} is not a directory"
            )

        sql_files = sorted(migrations_path.glob("*.sql"))

        if not sql_files:
            logger.warning(f"No .sql files found in {migrations_path}")
            return []

        result = []
        for file in sql_files:
            logger.info(f"Found script: {file.name}")
            result.append((file.name, file.read_text()))

        return result