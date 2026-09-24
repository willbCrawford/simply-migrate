import re
from typing import List, Dict, Tuple

from simply_migrate.models.models import ScriptType, MigrationScript

from simply_migrate.logging.logger import ContextLogger


class MigrationScriptValidator:
    """Validates migration directory structure and scripts"""

    # Expected naming pattern: V001__create_users_table.sql
    MIGRATION_PATTERN = re.compile(r'^V(\d*.\d*)__(.*)\.sql$')
    ROLLBACK_PATTERN = re.compile(r'^R(\d*.\d*)__(.*)\.sql$')
    SEED_PATTERN = re.compile(r'^S(\d*.\d*)__(.*)\.sql$')

    VALID_FOLDERS = ["migrations", "data", "hotfix", ""]

    def __init__(
            self,
            migrations_dir: str,
            dry_run: bool,
            logger: ContextLogger,
    ):
        self.migrations_dir = migrations_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.dry_run = dry_run
        self.logger = logger

    def validate_directory_structure(self) -> bool:
        """Validate that the migrations directory exists and has proper structure"""
        if not self.migrations_dir.exists():
            self.errors.append(f"Migrations directory does not exist: {self.migrations_dir}")
            return False

        if not self.migrations_dir.is_dir():
            self.errors.append(f"Migrations directory is not a directory: {self.migrations_dir}")
            return False

        # Check for any SQL files
        sql_files = list(self.migrations_dir.glob("*.sql"))
        if not sql_files:
            self.warnings.append("No .sql files found in migrations directory")

        return len(self.errors) == 0

    def load_scripts(self, scripts: List[Tuple[str, str]]) -> List[MigrationScript]:
        """Load and validate all migration scripts"""
        self.logger.info("Loading migration scripts")

        migration_scripts = []

        for file_name, content in sorted(scripts):
            self.logger.info(f"Found script: {file_name}")

            parsed = self.parse_script_filename(file_name)

            self.logger.info(f"Parsed script: {parsed}")

            if not parsed:
                self.logger.warning(
                    f"{file_name}: Filename doesn't match expected pattern "
                    f"(V###__description.sql, R###__description.sql, or S###__description.sql)"
                )
                continue

            script_type, version, description = parsed

            script = MigrationScript(
                filename=file_name,
                version=version,
                description=description.replace('_', ' '),
                script_type=script_type,
                content=content
            )

            # Validate content
            self.validate_script_content(script)
            migration_scripts.append(script)

        # Check for version conflicts
        if not self._check_version_conflicts(migration_scripts):
            return []

        return migration_scripts

    def _check_version_conflicts(self, scripts: List[MigrationScript]) -> bool:
        """Check for duplicate version numbers"""
        versions_seen: Dict[Tuple[ScriptType, str], str] = {}

        for script in scripts:
            key = (script.script_type, script.version)
            if key in versions_seen:
                self.logger.error(
                    f"Version conflict: {script.filename} and {versions_seen[key]} "
                    f"both use version {script.version}"
                )
                return False
            else:
                versions_seen[key] = script.filename

        return True

    def validate_script_content(self, script: MigrationScript) -> bool:
        """Validate the content of a migration script"""
        is_valid = True

        # Check if file is empty
        if not script.content.strip():
            self.logger.error(f"{script.filename}: Script is empty")
            is_valid = False

        # Check for common SQL issues
        content_lower = script.content.lower()

        # Warn about missing semicolons
        if not script.content.strip().endswith(';'):
            self.logger.warning(f"{script.filename}: Missing semicolon at end of script")

        # Check for dangerous operations without transactions
        dangerous_ops = ['drop table', 'drop database', 'truncate']
        if any(op in content_lower for op in dangerous_ops):
            if 'begin' not in content_lower or 'commit' not in content_lower:
                self.logger.warning(
                    f"{script.filename}: Dangerous operation without explicit transaction"
                )

        return is_valid

    def parse_script_filename(self, filename: str) -> Tuple[ScriptType, str, str]:
        """Parse a script filename and extract version and description"""
        # Try migration pattern
        match = self.MIGRATION_PATTERN.match(filename)
        if match:
            return ScriptType.MIGRATION, match.group(1), match.group(2)

        # Try rollback pattern
        match = self.ROLLBACK_PATTERN.match(filename)
        if match:
            return ScriptType.ROLLBACK, match.group(1), match.group(2)

        # Try seed pattern
        match = self.SEED_PATTERN.match(filename)
        if match:
            return ScriptType.SEED, match.group(1), match.group(2)

        return None

