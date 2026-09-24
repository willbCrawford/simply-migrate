from abc import ABC


class MigrationProgressTracker(ABC):
    """Defines interface for callbacks for migration progress"""

    def on_start(self, total_tenants: int) -> None:
        """Called once before any tenants are processed."""
        pass

    def on_tenant_start(self, tenant_id: str, tenant_name: str) -> None:
        """Called before each tenant begins."""
        pass

    def on_tenant_complete(self, tenant_id: str, tenant_name: str, success: bool) -> None:
        """Called after each tenant finishes — success or failure."""
        pass

    def on_finish(self) -> None:
        """Called once after all tenants have been processed."""
        pass


class ProgressTracker(MigrationProgressTracker):

    def on_start(self, total_tenants: int) -> None:
        super().on_start(total_tenants)

    def on_tenant_start(self, tenant_id: str, tenant_name: str) -> None:
        super().on_tenant_start(tenant_id, tenant_name)

    def on_tenant_complete(self, tenant_id: str, tenant_name: str, success: bool) -> None:
        super().on_tenant_complete(tenant_id, tenant_name, success)

    def on_finish(self) -> None:
        super().on_finish()