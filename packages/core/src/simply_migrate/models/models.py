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


class SimplyMigrateBackendSettings(str, Enum):
    CELERY="celery"
    LOCAL="local"

class SimplyMigrateRunner(str, Enum):
    CELERY="celery"
    LOCAL="local"

from dataclasses import dataclass, field
from enum import Enum

class ScriptType(str, Enum):
    """Types of migration scripts"""
    MIGRATION = "migration"
    ROLLBACK = "rollback"
    SEED = "seed"


@dataclass
class MigrationScript:
    """Represents a single migration script"""
    filename: str
    version: str
    description: str
    script_type: ScriptType
    content: str

    def __repr__(self):
        return f"MigrationScript(v{self.version}: {self.description})"

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "version": self.version,
            "description": self.description,
            "script_type": self.script_type.value,  # serialize enum to string
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MigrationScript":
        return cls(
            filename=data["filename"],
            version=data["version"],
            description=data["description"],
            script_type=ScriptType(data["script_type"]),  # deserialize back to enum
            content=data["content"],
        )


class TenantMigration:
    def __init__(self, tenant_id: str, tenant_name: str, connection_string: str):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.connection_string = connection_string


@dataclass(frozen=True)
class TenantConfig:
    tenant_key: str
    tenant_id: str
    tenant_name: str
    connection_string: str

    def __repr__(self) -> str:
        # Mask the connection string in any debug output
        masked = self.connection_string.split("@")[-1] if "@" in self.connection_string else "***"
        return (
            f"TenantConfig("
            f"id={self.tenant_id!r}, "
            f"name={self.tenant_name!r}, "
            f"conn=...@{masked})"
        )


class SourceType(str, Enum):
    LOCAL = "local"
    S3    = "s3"
    GCS   = "gcs"
    AZURE = "azure"


@dataclass
class SourceConfig:
    type:         str                   = "local"
    bucket:       str | None            = None
    region:       str                   = "us-east-1"
    path_prefix:  str                   = ""
    project:      str | None            = None
    account_url:  str | None            = None
    container:    str | None            = None
    options:      dict                  = field(default_factory=dict)


@dataclass
class TenantsFile:
    tenants: List[TenantConfig]
    source:  SourceConfig               = field(default_factory=SourceConfig)


class OnErrorPolicy(str, Enum):
    HALT         = "halt"
    HALT_TENANT  = "halt-tenant"
    CONTINUE     = "continue"


@dataclass
class ScriptEntry:
    path: str
    on_error: OnErrorPolicy | None = None   # None = inherit from parent


@dataclass
class ReleaseFile:
    version:           str
    description:       str
    scripts:           List[ScriptEntry]
    tenants:           List[TenantConfig]
    on_error:          OnErrorPolicy       = OnErrorPolicy.CONTINUE
    released_at:       str | None          = None
    statement_timeout: int                 = 60
    lock_timeout:      int                 = 10


@dataclass
class HotfixFile:
    hotfix: str
    description: str
    scripts: list[ScriptEntry]
    tenants: list[str]                      # required — no default
    on_error: OnErrorPolicy = OnErrorPolicy.HALT
    severity: str = "critical"
    released_at: str | None = None
