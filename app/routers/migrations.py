from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.routers.job_runner import start_migration_job, state_manager, get_job_status
from app.migration.validator import MigrationValidator
from app.routers.dependencies import (
    monitor_job_progress
)

from app.models.models import (
    ValidationResponse,
    ValidateMigrationsRequest,
    StartMigrationResponse,
    StartMigrationRequest,
    MigrationMode,
    JobStatusResponse,
    JobProgressResponse,
    TenantResultResponse,
    JobListItem
)

from typing import List

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/migrations",
    tags=["Migrations"]
)

@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate migration scripts",
)
async def validate_migrations(request: ValidateMigrationsRequest):
    """
    Validate migration scripts without executing them.

    Checks:
    - Directory structure
    - Filename patterns
    - Script content
    - Version conflicts
    """
    try:
        migration_validator = MigrationValidator(request.migrations_dir)

        # Validate directory structure
        if not migration_validator.validate_directory_structure():
            return ValidationResponse(
                valid=False,
                errors=migration_validator.errors,
                warnings=migration_validator.warnings,
                scripts_found=0,
                report=migration_validator.get_report()
            )

        # Load and validate scripts
        scripts = migration_validator.load_scripts()

        return ValidationResponse(
            valid=len(migration_validator.errors) == 0,
            errors=migration_validator.errors,
            warnings=migration_validator.warnings,
            scripts_found=len(scripts),
            report=migration_validator.get_report()
        )

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


# TODO: Create logic to store migration data in master database and to conditionally create tables if not exists or store in filesystem/remote storage
@router.post(
    "/start",
    response_model=StartMigrationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a migration job",
)
async def start_migration(
        request: StartMigrationRequest,
        background_tasks: BackgroundTasks
):
    """
    Start a migration job across multiple tenants.

    The job runs asynchronously. Use the returned job_id to track progress.
    """
    try:
        logger.info("Beginning processing of migration job")

        # Validate migrations first
        migration_validator = MigrationValidator(request.migrations_dir)

        if not migration_validator.validate_directory_structure():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid migrations directory",
                    "validation_errors": migration_validator.errors
                }
            )

        scripts = migration_validator.load_scripts()

        if migration_validator.errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Migration validation failed",
                    "validation_errors": migration_validator.errors,
                    "validation_warnings": migration_validator.warnings
                }
            )

        if not scripts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No migration scripts found"
            )

        # Generate job ID
        job_id = f"migration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(request.tenants)}_tenants"

        # Convert scripts to dict format for Celery
        script_dicts = [
            {
                'filename': s.filename,
                'content': s.content,
                'version': s.version,
                'description': s.description
            }
            for s in scripts
        ]

        # Start the migration job
        dry_run = request.mode == MigrationMode.DRY_RUN
        task = await start_migration_job(
            job_id=job_id,
            tenants=request.tenants,
            scripts=script_dicts,
            dry_run=dry_run,
            parallel=request.parallel
        )

        # Start background task to monitor progress
        background_tasks.add_task(monitor_job_progress, job_id)

        logger.info(f"Started migration job {job_id} with {len(request.tenants)} tenants")

        return StartMigrationResponse(
            job_id=job_id,
            task_id=task['job_id'],
            message=f"Migration job started for {len(request.tenants)} tenant(s)",
            status_url=f"/app/migrations/jobs/{job_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting migration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start migration: {str(e)}"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    tags=["Jobs"]
)
async def get_job(job_id: str):
    """
    Get the current status and progress of a migration job.
    """
    try:
        job_status = get_job_status(job_id)

        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Convert to response model
        return JobStatusResponse(
            job_id=job_status['job_id'],
            status=job_status['status'],
            progress=JobProgressResponse(**job_status['progress']),
            started_at=job_status['started_at'],
            completed_at=job_status['completed_at'],
            tenant_results={
                k: TenantResultResponse(**v)
                for k, v in job_status['tenant_results'].items()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}"
        )


@router.get(
    "/jobs",
    response_model=List[JobListItem],
    summary="List recent jobs",
    tags=["Jobs"]
)
async def list_jobs(limit: int = 50):
    """
    List recent migration jobs.
    """
    try:
        jobs = state_manager.get_all_jobs(limit=limit)

        return [
            JobListItem(
                job_id=job.job_id,
                status=job.status.value,
                total_tenants=job.total_tenants,
                successful_tenants=job.successful_tenants,
                failed_tenants=job.failed_tenants,
                started_at=job.started_at,
                completed_at=job.completed_at
            )
            for job in jobs
        ]

    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


# @app.post(
#     "/app/migrations/jobs/{job_id}/cancel",
#     summary="Cancel a job",
#     tags=["Jobs"]
# )
# async def cancel_migration_job(job_id: str):
#     """
#     Cancel a running migration job.
#
#     Note: Tasks already executing cannot be stopped immediately.
#     """
#     try:
#         success = cancel_job(job_id)
#
#         if not success:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Job {job_id} not found"
#             )
#
#         return {
#             "job_id": job_id,
#             "message": "Job cancellation requested",
#             "note": "Tasks already executing will complete"
#         }
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error canceling job: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to cancel job: {str(e)}"
#         )


@router.delete(
    "/jobs/{job_id}",
    summary="Delete job history",
    tags=["Jobs"]
)
async def delete_job(job_id: str):
    """
    Delete a job from history (does not affect execution).
    """
    try:
        key = f"{state_manager.job_prefix}{job_id}"
        deleted = state_manager.redis.delete(key)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        return {
            "job_id": job_id,
            "message": "Job history deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )
