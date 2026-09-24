from dataclasses import dataclass
from pathlib import Path
from typing import List

from simply_migrate.models.models import TenantConfig, ReleaseFile
from simply_migrate.source.base import ScriptSource
from simply_migrate.loader.release_loader import load_release
from simply_migrate.source.validator import MigrationScriptValidator, MigrationScript
from simply_migrate.logging.logger import ContextLogger

@dataclass
class ReleaseLoader:
    source:       ScriptSource
    release_file: str
    tenants_config: List[TenantConfig]
    base_path:    str = "."

    def load(self, logger: ContextLogger) -> tuple[ReleaseFile, List[MigrationScript]]:
        if self.release_file is None:
            raise FileNotFoundError()

        release_file = Path(f'release/{self.release_file}.yaml')

        if not release_file.is_file():
            raise FileExistsError()

        release = load_release(release_file=release_file, tenants_config=self.tenants_config)
        logger.info(f"Loading release {release.version!r} — {len(release.scripts)} script(s)")

        files = self.source.get_files(
            path=self.base_path,
            directory='',
            logger=logger,
        )

        raw = []
        for entry in release.scripts:
            script_path = Path(entry.path)

            matched = [(f, c) for f, c in files if f == script_path.name]
            if not matched:
                raise FileNotFoundError(
                    f"Script {entry.path!r} not found. "
                    f"Check the path in your release file."
                )
            raw.extend(matched)

        validator = MigrationScriptValidator(logger)
        return release, validator.load_scripts(raw)