from app.callback.callback_context import CallbackContext
from app.callback.callback_result import CallbackResult
from app.callback.specs import (
    MigrationCallbackSpec,
    migration_hook_spec,
    JobCallbackSpec,
    job_hook_spec
)

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomMigrationCallbackSpec:
    @migration_hook_spec
    
