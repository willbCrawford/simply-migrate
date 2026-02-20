import asyncio
import logging

from .job_runner import get_job_status
from .connection_manager import ConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

manager = ConnectionManager()

async def monitor_job_progress(job_id: str):
    """Monitor job progress and broadcast updates via WebSocket"""
    logger.info(f"Starting progress monitor for job {job_id}")

    while True:
        try:
            job_status = get_job_status(job_id)
            if not job_status:
                logger.warning(f"Job {job_id} not found")
                break

            # Broadcast current status
            await manager.broadcast_to_job(job_id, {
                "type": "progress_update",
                "data": job_status
            })

            # Stop monitoring if job is complete
            if job_status['status'] in ['success', 'failed', 'partial']:
                await manager.broadcast_to_job(job_id, {
                    "type": "job_complete",
                    "data": job_status
                })
                logger.info(f"Job {job_id} completed with status: {job_status['status']}")
                break

            await asyncio.sleep(2)  # Poll every 2 seconds

        except Exception as e:
            logger.error(f"Error monitoring job {job_id}: {e}", exc_info=True)
            await asyncio.sleep(5)

