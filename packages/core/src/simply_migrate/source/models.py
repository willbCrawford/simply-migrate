from dataclasses import dataclass
from enum import Enum

class ScriptType(str, Enum):
    VERSIONED  = "versioned"    # V1.2__description.sql
    UNDO       = "undo"         # U1.2__description.sql
    REPEATABLE = "repeatable"   # R__description.sql
    SEED       = "seed"         # S1.2__description.sql


@dataclass
class MigrationScript:
    filename:    str
    version:     str | None     # None for repeatable scripts
    description: str
    script_type: ScriptType
    content:     str
