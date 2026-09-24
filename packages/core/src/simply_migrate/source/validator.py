import re
from typing import List, Tuple

from simply_migrate.logging.logger import ContextLogger
from simply_migrate.source.models import MigrationScript, ScriptType

class MigrationScriptValidator:
    """
    Validates and parses SQL filenames using Flyway naming conventions.

    Versioned:   V{version}__{description}.sql   e.g. V1.2__add_users.sql
    Undo:        U{version}__{description}.sql   e.g. U1.2__add_users.sql
    Repeatable:  R__{description}.sql            e.g. R__seed_countries.sql
    Seed:        S{version}__{description}.sql   e.g. S1.2__seed_roles.sql

    Separator is double underscore (__).
    Version can be numeric with dots or underscores e.g. 1, 1.2, 1_2.
    """

    VERSIONED_PATTERN  = re.compile(r'^V([\d._]+)__([\w ]+)\.sql$',  re.IGNORECASE)
    UNDO_PATTERN       = re.compile(r'^U([\d._]+)__([\w ]+)\.sql$',  re.IGNORECASE)
    REPEATABLE_PATTERN = re.compile(r'^R__([\w ]+)\.sql$',           re.IGNORECASE)
    SEED_PATTERN       = re.compile(r'^S([\d._]+)__([\w ]+)\.sql$',  re.IGNORECASE)

    def __init__(self, logger: ContextLogger):
        self.logger = logger

    def load_scripts(
        self,
        raw: List[Tuple[str, str]],
    ) -> List[MigrationScript]:
        scripts = []

        for filename, content in raw:
            parsed = self._parse_filename(filename)
            if not parsed:
                self.logger.warning(
                    f"{filename}: Does not match Flyway naming convention — skipping.\n"
                    f"  Expected: V1.2__description.sql | R__description.sql | "
                    f"U1.2__description.sql | S1.2__description.sql"
                )
                continue

            script_type, version, description = parsed
            script = MigrationScript(
                filename=filename,
                version=version,
                description=description.replace("_", " "),
                script_type=script_type,
                content=content,
            )
            self._validate_content(script)
            scripts.append(script)

        if not self._check_version_conflicts(scripts):
            return []

        # Versioned scripts sorted by version, repeatables at the end
        return self._sort(scripts)

    def _parse_filename(
        self,
        filename: str,
    ) -> Tuple[ScriptType, str | None, str] | None:
        for pattern, script_type, has_version in [
            (self.VERSIONED_PATTERN,  ScriptType.VERSIONED,  True),
            (self.UNDO_PATTERN,       ScriptType.UNDO,        True),
            (self.SEED_PATTERN,       ScriptType.SEED,        True),
            (self.REPEATABLE_PATTERN, ScriptType.REPEATABLE,  False),
        ]:
            match = pattern.match(filename)
            if match:
                if has_version:
                    version     = match.group(1).replace("_", ".")
                    description = match.group(2)
                else:
                    version     = None
                    description = match.group(1)
                return script_type, version, description

        return None

    def _validate_content(self, script: MigrationScript) -> None:
        if not script.content.strip():
            self.logger.error(f"{script.filename}: Script is empty")

        if not script.content.strip().endswith(";"):
            self.logger.warning(f"{script.filename}: Missing semicolon at end of script")

        content_lower = script.content.lower()
        dangerous_ops = ["drop table", "drop database", "truncate"]
        if any(op in content_lower for op in dangerous_ops):
            if "begin" not in content_lower or "commit" not in content_lower:
                self.logger.warning(
                    f"{script.filename}: Dangerous operation without explicit transaction"
                )

    def _check_version_conflicts(self, scripts: List[MigrationScript]) -> bool:
        seen: dict[Tuple[ScriptType, str], str] = {}
        for script in scripts:
            if script.version is None:
                continue
            key = (script.script_type, script.version)
            if key in seen:
                self.logger.error(
                    f"Version conflict: {script.filename} and {seen[key]} "
                    f"both use version {script.version}"
                )
                return False
            seen[key] = script.filename
        return True

    def _sort(self, scripts: List[MigrationScript]) -> List[MigrationScript]:
        def sort_key(s: MigrationScript):
            if s.version is None:
                return 1, (999999,), s.filename  # repeatables last
            try:
                parts = tuple(int(x) for x in s.version.split("."))
            except ValueError:
                parts = (0,)
            return 0, parts, s.filename

        return sorted(scripts, key=sort_key)