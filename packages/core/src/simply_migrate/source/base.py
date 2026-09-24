from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple

from simply_migrate.logging.logger import ContextLogger


class ScriptSource(ABC):

    @abstractmethod
    def get_files(
        self,
        path: str,
        directory: str,
        logger: ContextLogger,
    ) -> List[Tuple[str, str]]:
        """
        Return all (filename, content) tuples for .sql files
        found at path/directory, sorted by filename.
        """