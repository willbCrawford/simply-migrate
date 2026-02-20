import importlib
import inspect
from typing import List, Callable
from .callback_context import CallbackContext
from .callback_result import CallbackResult
import logging
import pluggy

from .specs import MigrationCallbackSpec, JobCallbackSpec, MigrationFileSpec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationCallbackRegistry:
    def __init__(self):
        self.pm = pluggy.PluginManager("migration")
        self.pm.add_hookspecs(MigrationCallbackSpec)

    def register_plugin(self, plugin):
        self.pm.register(plugin)


class JobCallbackRegistry:
    def __init__(self):
        self.pm = pluggy.PluginManager("job")
        self.pm.add_hookspecs(JobCallbackSpec)

    def register_plugin(self, plugin):
        self.pm.register(plugin)

class MigrationFileRegistry:
    def __init__(self):
        self.pm = pluggy.PluginManager("migration_file")
        self.pm.add_hookspecs(MigrationFileSpec)

    def register_plugin(self, plugin):
        self.pm.register(plugin)


class CallbackRegistry:
    """Registry for callback functions"""

    def __init__(self):
        self.before_job_callbacks: List[Callable] = []
        self.after_job_callbacks: List[Callable] = []
        self.before_tenant_callbacks: List[Callable] = []
        self.after_tenant_callbacks: List[Callable] = []
        self.before_script_callbacks: List[Callable] = []
        self.after_script_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []

    def register_before_job(self, func: Callable):
        """Register callback to run before entire job starts"""
        self.before_job_callbacks.append(func)
        return func

    def register_after_job(self, func: Callable):
        """Register callback to run after entire job completes"""
        self.after_job_callbacks.append(func)
        return func

    def register_before_tenant(self, func: Callable):
        """Register callback to run before each tenant migration"""
        self.before_tenant_callbacks.append(func)
        return func

    def register_after_tenant(self, func: Callable):
        """Register callback to run after each tenant migration"""
        self.after_tenant_callbacks.append(func)
        return func

    def register_before_script(self, func: Callable):
        """Register callback to run before each script"""
        self.before_script_callbacks.append(func)
        return func

    def register_after_script(self, func: Callable):
        """Register callback to run after each script"""
        self.after_script_callbacks.append(func)
        return func

    def register_on_error(self, func: Callable):
        """Register callback to run when an error occurs"""
        self.on_error_callbacks.append(func)
        return func

    async def run_callbacks(self, callbacks: List[Callable], context: CallbackContext) -> CallbackResult:
        """Run a list of callbacks sequentially"""
        logger.info(f"Running callbacks: {callbacks}")
        logger.info(f"Running with callback context: {context}")
        for callback in callbacks:
            try:
                logger.info(f"Running callback: {callback.__name__}")

                # Check if callback is async
                if inspect.iscoroutinefunction(callback):
                    result = await callback(context)
                else:
                    result = callback(context)

                # Handle different return types
                if result is None:
                    continue
                elif isinstance(result, CallbackResult):
                    if not result.success or result.skip_script:
                        return result
                elif isinstance(result, bool):
                    if not result:
                        return CallbackResult.fail(f"Callback {callback.__name__} returned False")
                elif isinstance(result, dict):
                    context.metadata.update(result)

            except Exception as e:
                logger.error(f"Callback {callback.__name__} failed: {e}", exc_info=True)
                return CallbackResult.fail(f"Callback failed: {str(e)}")

        return CallbackResult.ok()

    def load_from_file(self, filepath: str):
        """Load callbacks from a Python file"""
        try:
            spec = importlib.util.spec_from_file_location("callbacks", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for decorated functions or explicit registration
            for name, obj in inspect.getmembers(module):
                if callable(obj) and hasattr(obj, '_callback_type'):
                    logging.info(f"about to evaluate switch case: {obj._callback_type}")

                    callback_type = obj._callback_type
                    if callback_type == 'before_job':
                        logging.info(f"about to add a new callback: {callback_type}")
                        self.register_before_job(obj)
                    elif callback_type == 'after_job':
                        logging.info(f"about to add a new callback: {callback_type}")
                        self.register_after_job(obj)
                    elif callback_type == 'before_tenant':
                        logging.info(f"about to add a new callback: {callback_type}")
                        self.register_before_tenant(obj)
                    elif callback_type == 'after_tenant':
                        logging.info(f"about to add a new callback: {callback_type}")
                        self.register_after_tenant(obj)
                    elif callback_type == 'before_script':
                        logging.info(f"about to add a new callback: {callback_type}")
                        self.register_before_script(obj)
                    elif callback_type == 'after_script':
                        logging.info(f"about to add a new callback: {callback_type}")
                        self.register_after_script(obj)
                    elif callback_type == 'on_error':
                        logging.info(f"about to add a new callback: {callback_type}")
                        self.register_on_error(obj)

            logger.info(f"Loaded callbacks from {filepath}")

        except Exception as e:
            logger.error(f"Failed to load callbacks from {filepath}: {e}", exc_info=True)
            raise
