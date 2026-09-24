import hashlib
from datetime import datetime
from sqlalchemy import text, Engine

from simply_migrate.backend.migration_record import MigrationRecord, MigrationRecordStatus
from simply_migrate.logging.logger import ContextLogger

import re

VERSION_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?$")  # 1.0, 1.0.0

def validate_version(version: str) -> str:
    """Validate version string to prevent any injection via version field"""
    if not VERSION_PATTERN.match(version):
        raise ValueError(f"Invalid version format: '{version}'. Expected format: 1.0 or 1.0.0")
    return version


FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+\.sql$")

def validate_filename(filename: str) -> str:
    """Validate filename to prevent any injection via filename field"""
    if not FILENAME_PATTERN.match(filename):
        raise ValueError(f"Invalid filename: '{filename}'. Only alphanumeric, underscores, hyphens allowed.")
    return filename

def compute_checksum(content: str) -> str:
    """MD5 checksum of script content to detect changes"""
    return hashlib.md5(content.encode()).hexdigest()


def has_script_been_applied(
        engine: Engine,
        version: str,
        filename: str,
        content: str,
        logger: ContextLogger
) -> bool:
    """Check if a script has already been successfully applied"""

    version = validate_version(version)
    filename = validate_filename(filename)

    script_checksum = compute_checksum(content)
    query = text("""
        SELECT checksum FROM _simply_migrate_history
        WHERE version = :version
        AND filename = :filename
        AND status = 'success'
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"version": version, "filename": filename})
        checksums = [row[0] for row in result]

        logger.info(f"Checksum for {version}:{filename}: {checksums}")

        if len(checksums) > 1:
            raise ValueError(f"More than one checksum found for this version: {version}")

        if len(checksums) == 0:
            logger.info(f"No checksum found for this version: {version}")
            return False

        return checksums[0] == script_checksum


def record_migration_start(
        engine: Engine,
        record: MigrationRecord
) -> int:
    """Insert a pending record and return its id"""
    query = text("""
        INSERT INTO _simply_migrate_history
            (version, filename, description, script_type, status, checksum, executed_at)
        VALUES
            (:version, :filename, :description, :script_type, :status, :checksum, :executed_at)
        RETURNING id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {
            "version": record.version,
            "filename": record.filename,
            "description": record.description,
            "script_type": record.script_type,
            "status": MigrationRecordStatus.PENDING.value,
            "checksum": record.checksum,
            "executed_at": datetime.utcnow(),
        })
        conn.commit()
        return result.scalar()


def record_migration_complete(
        engine: Engine,
        record_id: int,
        execution_time: int,
        logger: ContextLogger
):
    """Mark a migration record as successful"""
    query = text("""
        UPDATE _simply_migrate_history
        SET status = 'success', execution_time = :execution_time
        WHERE id = :id
    """)
    with engine.connect() as conn:
        conn.execute(query, {"id": record_id, "execution_time": execution_time})
        conn.commit()
    logger.info(f"Migration {record_id} completed in {execution_time}ms")


def record_migration_failed(
        engine: Engine,
        record_id: int,
        error_message: str,
        execution_time: int,
        logger: ContextLogger
):
    """Mark a migration record as failed"""
    query = text("""
        UPDATE _simply_migrate_history
        SET status = 'failed', error_message = :error_message, execution_time = :execution_time
        WHERE id = :id
    """)
    with engine.connect() as conn:
        conn.execute(query, {
            "id": record_id,
            "error_message": error_message,
            "execution_time": execution_time,
        })
        conn.commit()
    logger.error(f"Migration {record_id} failed: {error_message}")


def get_applied_versions(engine: Engine) -> list[str]:
    """Return all successfully applied versions in order"""
    query = text("""
        SELECT DISTINCT version FROM _simply_migrate_history
        WHERE status = 'success'
        ORDER BY version
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        return [row[0] for row in result]
