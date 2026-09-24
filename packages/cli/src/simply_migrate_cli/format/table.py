from rich.table import Table

from typing import List

from simply_migrate.backend.models import TenantMigrationResult
from simply_migrate.models.models import MigrationScript


def create_script_table(scripts: List[MigrationScript]) -> Table:
    table = Table('Script Type', 'Description', 'Version')
    table.title = 'Migration Scripts'

    for script in scripts:
        table.add_row(script.script_type, script.description, script.version)

    return table

def create_migration_table(migration_results: List[TenantMigrationResult]) -> Table:
    table = Table('Tenant Name', 'Scripts Passed', 'Scripts Failed', 'Status')
    table.title = 'Tenant Migrations'

    for result in migration_results:
        scripts_applied = len(result.scripts_applied)
        scripts_failed = len(result.scripts_failed)
        table.add_row(result.tenant_id, f'{scripts_applied}', f'{'[bold red]' if scripts_failed > 0 else ''}{scripts_failed}{'[/bold red]' if scripts_failed > 0 else ''}', result.status)

    return table