from celery import group, chord
import redis

import asyncio

from typing import List, Dict, Optional, Any

from app.callback.callback_context import CallbackContext
from app.callback.callback_registry import CallbackRegistry
from app.models.models import StartMigrationTenantRequest
from app.migration_queue.state_management import StateManager
from app.worker import apply_migration_to_tenant, finalize_migration_job

import logging

import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
state_manager = StateManager(redis_client)
callback_registry = CallbackRegistry()


async def start_migration_job(
        job_id: str,
        tenants: List[StartMigrationTenantRequest],
        scripts: List[Dict],
        dry_run: bool = False,
        parallel: bool = True,
) -> Dict[str, Any]:
    """Start a migration job with optional callback file"""

    try:
        callback_file = os.environ['SIMPLY_MIGRATE_CALLBACK_FILE']

        # Load callbacks if file provided
        if callback_file:
            callback_registry.load_from_file(callback_file)
    except KeyError as e:
        logger.info(f"Could not load the callback file. Environment variable was never supplied")

    logger.info(f"{{ job_id: '{job_id}', tenants: [{tenants}], scripts: [{scripts}], dry_run: {dry_run}, parallel: {parallel}, callback_file: {callback_file} }}")

    # Run before_job callbacks
    try:
        context = CallbackContext(
            job_id=job_id,
            tenant_id="",
            script={},
            scripts=scripts,
            current_script_index=-1,
            metadata={'tenants': tenants}
        )

        callback_result = await callback_registry.run_callbacks(
            callback_registry.before_job_callbacks,
            context
        )

        if not callback_result:
            raise Exception(f"Before job callback failed: {callback_result.message}")
    except Exception as e:
        logger.error(f"Failed to run before_job callbacks: {e}")
        raise

    # Create job in state manager
    state_manager.create_job(job_id, tenants)

    logger.info(f"Starting migration job {job_id} for {len(tenants)} tenants")

    if parallel:
        logger.info("Creating parallel task group...")

        # Create task signatures for all tenants
        tenant_tasks = group([
            apply_migration_to_tenant.si(
                job_id,
                tenant.tenant_id,
                tenant.tenant_name,
                tenant.user,
                tenant.password,
                tenant.database_name,
                tenant.host,
                tenant.connection_string,
                scripts,
                dry_run
            )
            for tenant in tenants
        ])

        # Create callback
        callback = finalize_migration_job.si(job_id)

        # Execute chord - THIS IS THE KEY
        result = chord(tenant_tasks, callback)()

        # logger.info(f"result of chord {result.get()}")

        logger.info(f"Parallel migration started - Chord ID: {result.id}")
        logger.info(f"Queued {len(tenants)} tenant tasks")

        return {
            'job_id': job_id,
            'task_ids': [result.id],
            'task_type': 'chord',
            'tenant_count': len(tenants),
            'mode': 'parallel'
        }

    else:
        logger.info("Creating sequential task chain...")

        task_ids = []

        for i, tenant in enumerate(tenants):
            is_last = (i == len(tenants) - 1)

            # Build the task
            if is_last:
                # Last task triggers the finalize callback
                result = apply_migration_to_tenant.apply_async(
                    args=[
                        job_id,
                        tenant.tenant_id,
                        tenant.tenant_name,
                        tenant.user,
                        tenant.password,
                        tenant.database_name,
                        tenant.host,
                        tenant.connection_string,
                        scripts,
                        dry_run
                    ],
                    link=finalize_migration_job.si(job_id)
                )
            else:
                result = apply_migration_to_tenant.apply_async(
                    args=[
                        job_id,
                        tenant.tenant_id,
                        tenant.tenant_name,
                        tenant.user,
                        tenant.password,
                        tenant.database_name,
                        tenant.host,
                        tenant.connection_string,
                        scripts,
                        dry_run
                    ],
                )

            logger.info(f"result: {result}")

            task_ids.append(result.id)
            logger.info(f"Queued tenant {tenant} - Task ID: {result.id}")

        logger.info(f"Sequential migration started - {len(task_ids)} tasks queued")

        return {
            'job_id': job_id,
            'task_ids': task_ids,
            'task_type': 'sequential',
            'tenant_count': len(tenants),
            'mode': 'sequential'
        }


def get_job_status(job_id: str) -> Optional[Dict]:
    """Get the current status of a migration job"""
    job = state_manager.get_job(job_id)
    if not job:
        return None

    return {
        'job_id': job.job_id,
        'status': job.status,
        'progress': {
            'total': job.total_tenants,
            'completed': job.completed_tenants,
            'successful': job.successful_tenants,
            'failed': job.failed_tenants,
            'percent': (job.completed_tenants / job.total_tenants * 100) if job.total_tenants > 0 else 0
        },
        'started_at': job.started_at,
        'completed_at': job.completed_at,
        'tenant_results': {
            k: {
                'status': v.status,
                'scripts_applied': v.scripts_applied,
                'scripts_skipped': v.scripts_skipped,
                'callback_metadata': v.callback_metadata,
                'error_message': v.error_message,
                'duration_seconds': v.duration_seconds
            }
            for k, v in job.tenant_results.items()
        }
    }


# def cancel_job(job_id: str) -> bool:
#     """Cancel a running migration job"""
#     job = state_manager.get_job(job_id)
#     if not job:
#         return False
#
#     app.control.revoke(job_id, terminate=True)
#     state_manager.update_job_status(job_id, MigrationStatus.FAILED)
#     logger.warning(f"Migration job {job_id} cancelled")
#     return True


def _run_error_callbacks(job_id: str, tenant_id: str, error_message: str, callback_registry: CallbackRegistry):
    """Run error callbacks"""
    # try:
    #     context = CallbackContext(
    #         job_id=job_id,
    #         tenant_id=tenant_id,
    #         script={},
    #         scripts=[],
    #         current_script_index=-1,
    #         metadata={'error': error_message}
    #     )
    #     callback_registry.run_callbacks(callback_registry.on_error_callbacks, context)
    # except Exception as e:
    #     logger.error(f"Error callback failed: {e}", exc_info=True)
