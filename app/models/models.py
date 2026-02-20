from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class MigrationMode(str, Enum):
    """Migration execution mode"""
    DRY_RUN = "dry_run"
    APPLY = "apply"
    VALIDATE_ONLY = "validate_only"


class StartMigrationTenantRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID can be guid, int anything to identify tenants in logs")
    tenant_name: Optional[str] = Field(..., description="Optional human readable tenant name")
    user: str = Field(..., description="user name to connect to database")
    password: str = Field(..., description="password to connect to database")
    database_name: str = Field(..., description="Database name to connect to database")
    host: Optional[str] = Field(..., description="Database host")
    connection_string: Optional[str] = Field(..., description="Connection string to connect to database")


class StartMigrationRequest(BaseModel):
    """Request to start a migration job"""
    tenants: List[StartMigrationTenantRequest] = Field(..., description="List of tenant identifiers")
    migrations_dir: str = Field(..., description="Path to migrations directory")
    mode: MigrationMode = Field(default=MigrationMode.DRY_RUN, description="Execution mode")
    parallel: bool = Field(default=True, description="Execute migrations in parallel")
    job_name: Optional[str] = Field(None, description="Optional human-readable job name")


class ValidateMigrationsRequest(BaseModel):
    """Request to validate migrations without executing"""
    migrations_dir: str = Field(..., description="Path to migrations directory")


class TenantResultResponse(BaseModel):
    """Response model for tenant migration result"""
    tenant_id: str
    status: str
    scripts_applied: List[str]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[float]


class JobProgressResponse(BaseModel):
    """Response model for job progress"""
    total: int
    completed: int
    successful: int
    failed: int
    percent: float


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    progress: JobProgressResponse
    started_at: str
    completed_at: Optional[str]
    tenant_results: Dict[str, TenantResultResponse]
    job_name: Optional[str] = None


class JobListItem(BaseModel):
    """Response model for job list item"""
    job_id: str
    status: str
    total_tenants: int
    successful_tenants: int
    failed_tenants: int
    started_at: str
    completed_at: Optional[str]
    job_name: Optional[str] = None


class StartMigrationResponse(BaseModel):
    """Response when starting a migration"""
    job_id: str
    task_id: str
    message: str
    status_url: str


class ValidationResponse(BaseModel):
    """Response for validation request"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    scripts_found: int
    report: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
