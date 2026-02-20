from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class ScriptType(Enum):
    """Types of migration scripts"""
    MIGRATION = "migration"
    ROLLBACK = "rollback"
    SEED = "seed"


@dataclass
class MigrationScript:
    """Represents a single migration script"""
    filename: str
    filepath: Path
    version: str
    description: str
    script_type: ScriptType
    content: str

    def __repr__(self):
        return f"MigrationScript(v{self.version}: {self.description})"
