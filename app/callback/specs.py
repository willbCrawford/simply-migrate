import importlib
import inspect
from typing import List, Callable
from .callback_context import CallbackContext
from .callback_result import CallbackResult
import logging
import pluggy

job_hook_spec = pluggy.HookspecMarker("job")
migration_hook_spec = pluggy.HookspecMarker("migration")
migration_file_spec = pluggy.HookspecMarker("migration_file")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    def before_tenant(self, context: CallbackContext):
        """Run before each tenant starts migration"""

    @migration_hook_spec
    def after_tenant(self, context: CallbackContext):
        """Run after each tenant completes"""

    @migration_hook_spec
    def before_script(self, context: CallbackContext):
        """Run before each script starts"""

    @migration_hook_spec
    def after_script(self, context: CallbackContext):
        """Run after each script completes"""


class MigrationFileSpec:
    @migration_hook_spec
    def get_files(self, context: CallbackContext):
        """Get the files. By default, it will pull from the migrations folder. You can override this with an environment variable."""