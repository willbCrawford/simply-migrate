from dataclasses import dataclass
from typing import List

from simply_migrate.source.base import ScriptSource
from simply_migrate.source.validator import MigrationScriptValidator, MigrationScript
from simply_migrate.logging.logger import ContextLogger


@dataclass
class MigrationScriptLoader:
    source:          ScriptSource
    path:            str
    directory:       str
    version_ceiling: str | None = None

    def load(self, logger: ContextLogger) -> List[MigrationScript]:
        raw = self.source.get_files(path=self.path, directory=self.directory, logger=logger)
        validator = MigrationScriptValidator(logger)
        scripts = validator.load_scripts(raw)

        if self.version_ceiling:
            scripts = [
                s for s in scripts
                if s.version and _version_lte(s.version, self.version_ceiling)
            ]
            logger.info(
                f"Version ceiling {self.version_ceiling!r} — "
                f"{len(scripts)} script(s) in scope"
            )

        return scripts


def _version_lte(script_version: str, ceiling: str) -> bool:
    def parse(v):
        return tuple(int(x) for x in v.replace("_", ".").split("."))
    try:
        return parse(script_version) <= parse(ceiling)
    except ValueError:
        return True