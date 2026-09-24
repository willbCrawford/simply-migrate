from enum import Enum

from dataclasses import dataclass

from typing import Any, Dict, List, Optional


class MigrationStatus(str, Enum):
    """Status of migration execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"  # Some tenants succeeded, some failed


@dataclass
class TenantMigrationResult:
    """Result of migration for a single tenant"""
    tenant_id: str
    status: MigrationStatus
    scripts_applied: List[str]
    scripts_skipped: List[str]
    scripts_failed: List[str]
    callback_metadata: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None


@dataclass
class MigrationJobState:
    """Overall state of a migration job"""
    job_id: str
    status: MigrationStatus
    tenants: List[str]
    total_tenants: int
    completed_tenants: int
    successful_tenants: int
    failed_tenants: int
    tenant_results: Dict[str, TenantMigrationResult]
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
