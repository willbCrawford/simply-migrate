import redis
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict

from app.models.models import StartMigrationTenantRequest

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


class StateManager:
    """Manages migration job state in Redis"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.job_prefix = "migration:job:"
        self.tenant_prefix = "migration:tenant:"

    def get_job_dict(self, data: str):
        job_dict = json.loads(data)

        job_dict['status'] = job_dict['status']
        job_dict['tenant_results'] = {
            k: TenantMigrationResult(**{**v, 'status': v['status']})
            for k, v in job_dict.get('tenant_results', {}).items()
        }

        return job_dict

    def create_job(self, job_id: str, tenants: List[StartMigrationTenantRequest]) -> MigrationJobState:
        """Create a new migration job"""
        state = MigrationJobState(
            job_id=job_id,
            status=MigrationStatus.PENDING,
            tenants=[tenant.tenant_name for tenant in tenants],
            total_tenants=len(tenants),
            completed_tenants=0,
            successful_tenants=0,
            failed_tenants=0,
            tenant_results={},
            started_at=datetime.utcnow().isoformat()
        )
        self._save_job(state)
        return state

    def get_job(self, job_id: str) -> Optional[MigrationJobState]:
        """Retrieve job state"""
        key = f"{self.job_prefix}{job_id}"
        data = self.redis.get(key)
        if not data:
            return None

        job_dict = self.get_job_dict(data)

        return MigrationJobState(**job_dict)

    def update_job_status(self, job_id: str, status: MigrationStatus):
        """Update overall job status"""
        job = self.get_job(job_id)
        if job:
            job.status = status
            if status in [MigrationStatus.SUCCESS, MigrationStatus.FAILED, MigrationStatus.PARTIAL]:
                job.completed_at = datetime.utcnow().isoformat()
            self._save_job(job)

    def update_tenant_result(self, job_id: str, tenant_result: TenantMigrationResult):
        """Update result for a specific tenant"""
        job = self.get_job(job_id)
        if not job:
            return

        job.tenant_results[tenant_result.tenant_id] = tenant_result
        job.completed_tenants += 1

        if tenant_result.status == MigrationStatus.SUCCESS:
            job.successful_tenants += 1
        elif tenant_result.status == MigrationStatus.FAILED:
            job.failed_tenants += 1

        if job.completed_tenants == job.total_tenants:
            if job.failed_tenants == 0:
                job.status = MigrationStatus.SUCCESS
            elif job.successful_tenants == 0:
                job.status = MigrationStatus.FAILED
            else:
                job.status = MigrationStatus.PARTIAL
            job.completed_at = datetime.utcnow().isoformat()

        self._save_job(job)

    def serialize_for_celery(self, obj):
        """Convert objects to JSON-serializable format for Celery"""
        from dataclasses import asdict, is_dataclass
        from enum import Enum
        from datetime import datetime

        if isinstance(obj, Enum):
            return obj.value
        elif is_dataclass(obj):
            result = asdict(obj)
            # Recursively serialize nested objects
            return {k: self.serialize_for_celery(v) for k, v in result.items()}
        elif isinstance(obj, dict):
            return {k: self.serialize_for_celery(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.serialize_for_celery(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def _save_job(self, job: MigrationJobState):
        """Save job state to Redis"""
        print(f"going to save the following job: {self.serialize_for_celery(job.tenant_results)}")

        key = f"{self.job_prefix}{job.job_id}"
        job_dict = asdict(job)
        job_dict['status'] = job.status.value
        job_dict['tenant_results'] = self.serialize_for_celery(job.tenant_results)
        self.redis.setex(key, 86400 * 7, json.dumps(job_dict))

    def get_all_jobs(self, limit: int = 50) -> List[MigrationJobState]:
        """Get recent migration jobs"""
        keys = self.redis.keys(f"{self.job_prefix}*")
        jobs = []
        for key in keys[:limit]:
            data = self.redis.get(key)
            if data:
                job_dict = self.get_job_dict(data)
                jobs.append(MigrationJobState(**job_dict))
        return sorted(jobs, key=lambda x: x.started_at, reverse=True)


class DatabaseConnectionManager:
    """Manages database connections for tenants"""

    def __init__(self):
        self.connections = {}

    @staticmethod
    def get_connection_string(user: str, password:str, database_name: str, host='localhost') -> str:
        """Get database connection string for a tenant"""
        return f"postgresql://{user}:{password}@{host}:5432/{database_name}"

    def execute_script(self, user: str, password: str, database_name: str, host: str, connection_string: str, script_content: str) -> Dict:
        """Execute a migration script for a tenant"""
        from sqlalchemy import create_engine, text

        if connection_string is None or connection_string == "":
            connection_string = self.get_connection_string(user, password, database_name, host)

        engine = create_engine(connection_string)

        try:
            with engine.connect() as conn:
                trans = conn.begin()
                try:
                    conn.execute(text(script_content))
                    trans.commit()
                    return {"success": True, "message": "Script executed successfully"}
                except Exception as e:
                    trans.rollback()
                    raise e
        finally:
            engine.dispose()
