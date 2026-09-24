from sqlalchemy import Engine

from simply_migrate.backend.execute_scripts import execute_script
from simply_migrate.logging.logger import ContextLogger

CREATE_MIGRATION_HISTORY_TABLE = """
    CREATE TABLE IF NOT EXISTS _simply_migrate_history (
        id              SERIAL PRIMARY KEY,
        version         VARCHAR(50)     NOT NULL,
        filename        VARCHAR(255)    NOT NULL,
        description     VARCHAR(255),
        script_type     VARCHAR(50)     NOT NULL,
        status          VARCHAR(50)     NOT NULL,
        checksum        VARCHAR(64),
        executed_at     TIMESTAMP       NOT NULL DEFAULT NOW(),
        execution_time  INTEGER,
        error_message   TEXT
    );
"""

CREATE_MIGRATION_LOG_TABLE = """
    CREATE TABLE IF NOT EXISTS _simply_migrate_log (
        id              SERIAL PRIMARY KEY,
        job_id          VARCHAR(255)    NOT NULL,
        tenant_id       VARCHAR(255)    NOT NULL,
        version         VARCHAR(50),
        status          VARCHAR(50)     NOT NULL,
        started_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
        completed_at    TIMESTAMP,
        error_message   TEXT
    );
"""


def ensure_migration_history_table(engine: Engine, logger: ContextLogger) -> bool:
    """Create system tables if they do not exist. Called before every migration run."""
    try:
        logger.info("Ensuring system tables exist")
        execute_script(engine=engine, script_content=CREATE_MIGRATION_HISTORY_TABLE)
        logger.info("System tables ready")
        return True
    except Exception as e:
        logger.error(f"Failed to create system tables: {e}")
        return False


def ensure_migration_log_table(engine: Engine, logger: ContextLogger) -> bool:
    """Create system tables if they do not exist. Called before every migration run."""
    try:
        logger.info("Ensuring system tables exist")
        execute_script(engine=engine, script_content=CREATE_MIGRATION_LOG_TABLE)
        logger.info("System tables ready")
        return True
    except Exception as e:
        logger.error(f"Failed to create system tables: {e}")
        return False