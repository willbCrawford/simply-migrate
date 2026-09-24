import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple
from simply_migrate.logging.logger import ContextLogger
from simply_migrate.plugins.hook_specs import (
    job_hook_spec,
    migration_hook_spec,
    migration_file_spec
)
from simply_migrate.plugins.callback_result import CallbackResult
from simply_migrate.plugins.callback_context import CallbackContext
from simply_migrate.logging.logger import ContextLogger
from simply_migrate.plugins.implementation import LocalMigrationFilePlugin


class JobCallbackSpec:
    @job_hook_spec
    def before_job(self, context: CallbackContext):
        """Run before entire job starts"""

    @job_hook_spec
    def after_job(self, context: CallbackContext):
        """Run after entire job completes"""


class MigrationCallbackSpec:
    @migration_hook_spec
    def get_connection_string(self, context: CallbackContext):
        """Get the connection string"""

    @migration_hook_spec
    def before_tenant(self, context: CallbackContext) -> CallbackResult | None:
        """Run before each tenant starts migration"""

    @migration_hook_spec
    def after_tenant(self, context: CallbackContext) -> CallbackResult | None:
        """Run after each tenant completes"""

    @migration_hook_spec
    def before_script(self, context: CallbackContext) -> CallbackResult | None:
        """Run before each script starts"""

    @migration_hook_spec
    def after_script(self, context: CallbackContext) -> CallbackResult | None:
        """Run after each script completes"""



class MigrationFileSpec:

    @migration_file_spec(firstresult=True)
    def get_files(
        self,
        path: str,
        directory: str,
        logger: ContextLogger,
    ) -> List[Tuple[str, str]] | None:
        """
        Return all (filename, content) tuples found at path/directory.
        Used by: migrate command (directory scan)
        """

    @migration_hook_spec(firstresult=True)
    def get_file(
        self,
        path: str,
        logger: ContextLogger,
    ) -> Tuple[str, str] | None:
        """
        Return a single (filename, content) tuple for the given path.
        Used by: release and hotfix commands (explicit script entries)
        path is the full relative path e.g. 'migrations/V001__create_accounts.sql'
        """


class RemoteMigrationFilePlugin(ABC):
    """
    Base class for remote script sources.

    Subclasses implement _sync() to bulk-download scripts from a remote
    source into a local temp directory. All parsing is delegated to
    LocalMigrationFilePlugin — remote plugins never touch SQL content.
    """

    def __init__(self):
        self._local = LocalMigrationFilePlugin()

    @migration_file_spec
    def get_files(
        self,
        path: str,
        directory: str,
        logger: ContextLogger,
    ) -> List[Tuple[str, str]] | None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            logger.info(
                f"[{self.__class__.__name__}] Syncing {path}/{directory} "
                f"to local temp directory"
            )

            synced = self._sync(
                path=path,
                directory=directory,
                local_dir=tmp_path,
                logger=logger,
            )

            if not synced:
                return None

            logger.info(
                f"[{self.__class__.__name__}] Sync complete — "
                f"handing off to LocalMigrationFilePlugin"
            )

            # Delegate all parsing to local plugin
            return self._local.get_files(
                path=str(tmp_path),
                directory=directory,
                logger=logger,
            )

    @migration_file_spec
    def get_file(
        self,
        path: str,
        logger: ContextLogger,
    ) -> Tuple[str, str] | None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            script_path = Path(path)

            logger.info(
                f"[{self.__class__.__name__}] Fetching {path} "
                f"to local temp directory"
            )

            synced = self._sync(
                path="",
                directory=str(script_path.parent),
                local_dir=tmp_path,
                logger=logger,
            )

            if not synced:
                return None

            return self._local.get_file(
                path=str(tmp_path / path),
                logger=logger,
            )

    @abstractmethod
    def _sync(
        self,
        path: str,
        directory: str,
        local_dir: Path,
        logger: ContextLogger,
    ) -> bool:
        """
        Bulk download all .sql files from the remote source into local_dir,
        preserving the directory structure.

        Returns True if sync succeeded, False if the source could not be reached
        or the path does not exist.
        """

