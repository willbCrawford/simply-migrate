from datetime import datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.routers.job_runner import state_manager

router = APIRouter(
    prefix="/app/health",
)

@router.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connectivity
        state_manager.redis.ping()
        return {
            "status": "healthy",
            "redis": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
