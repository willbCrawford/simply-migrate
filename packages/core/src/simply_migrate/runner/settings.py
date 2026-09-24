from typing import List

class SimplyMigrateRunnerSettings:
    def __init__(
        self,
        job_id: str,
        version: str,
        migrations_dir: str,
        output_file: str,
        validate_only: bool,
        dry_run: bool
    ):
        self.job_id = job_id
        self.version = version
        self.migrations_dir = migrations_dir
        self.output_file = output_file
        self.validate_only = validate_only
        self.dry_run = dry_run

