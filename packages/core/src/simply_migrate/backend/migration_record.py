from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MigrationRecordStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MigrationRecord:
    version: str
    filename: str
    description: str
    script_type: str
    status: MigrationRecordStatus
    checksum: str | None = None
    executed_at: datetime | None = None
    execution_time: int | None = None  # milliseconds
    error_message: str | None = None
