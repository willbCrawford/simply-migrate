from simply_migrate.progress_tracker.migration_progress_tracker import MigrationProgressTracker

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskID,
)
from rich.console import Console

class RichProgressTracker(MigrationProgressTracker):
    _progress: Progress = None
    _task: TaskID = None
    _console = Console(stderr=True)  # stderr keeps stdout clean
    _total_tenants: int = 0
    _completed_tenants: int = 0

    def on_start(self, total_tenants: int) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TextColumn("{task.fields[status]}"),
            console=self._console,
        )
        self._progress.start()
        self._task = self._progress.add_task(
            description="Migrating tenants...",
            total=total_tenants,
            status=f"0/{total_tenants} complete",
        )
        self._total_tenants = total_tenants

    def on_tenant_start(self, tenant_id: str, tenant_name: str) -> None:
        if self._progress is None:
            return
        self._progress.update(
            self._task,
            description=f"Migrating [bold]{tenant_name}[/bold]...",
        )

    def on_tenant_complete(self, tenant_id: str, tenant_name: str, success: bool) -> None:
        if self._progress is None or self._task is None:
            return

        self._completed_tenants += 1
        completed  = self._completed_tenants
        total      = self._total_tenants
        icon       = "✓" if success else "✗"
        status_str = f"{icon} {tenant_name} | {completed}/{total} complete"

        self._progress.update(
            self._task,
            advance=1,
            status=status_str,
        )

    def on_finish(self) -> None:
        if self._progress is None:
            return
        self._progress.update(
            self._task,
            description="[bold green]Migration complete[/bold green]",
        )
        self._progress.stop()
