from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import (healthcheck, migrations)
from app.models.models import ErrorResponse

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Simply Migrate",
        description="API for managing database migrations across multiple tenants",
        version="1.0.0",
        docs_url="/foo/docs",
        redoc_url="/foo/redoc"
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(healthcheck.router)
    app.include_router(migrations.router)

    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "service": "Database Migration API",
            "version": "1.0.0",
            "status": "operational",
            "docs": "/foo/docs"
        }

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Custom HTTP exception handler"""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail if isinstance(exc.detail, str) else "Request failed",
                detail=exc.detail if not isinstance(exc.detail, str) else None
            ).dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """General exception handler"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal server error",
                detail=str(exc) if app.debug else None
            ).dict()
        )

    # ============================================================================
    # Startup/Shutdown Events
    # ============================================================================

    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        logger.info("Migration API starting up...")
        try:
            # Test Redis connection
            # state_manager.redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info("Migration API shutting down...")
        # Close any open connections
        # for job_id in list(manager.active_connections.keys()):
        #     for connection in manager.active_connections[job_id]:
        #         await connection.close()

    return app