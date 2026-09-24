import pluggy

from simply_migrate.plugins.specs import MigrationCallbackSpec, JobCallbackSpec, MigrationFileSpec

# TODO: Create better dependency injection for connection strings, before/after migrations, and before/after tenants
class MigrationCallbackRegistry:
    def __init__(self):
        self.pm = pluggy.PluginManager("migration")
        self.pm.add_hookspecs(MigrationCallbackSpec)

    def register_plugin(self, plugin):
        self.pm.register(plugin)


# TODO: Create better dependency injection for before/after job
class JobCallbackRegistry:
    def __init__(self):
        self.pm = pluggy.PluginManager("job")
        self.pm.add_hookspecs(JobCallbackSpec)

    def register_plugin(self, plugin):
        self.pm.register(plugin)

# TODO: Create AWS, AZURE AND GCP plugins to get files from s3, storage accounts etc.
class MigrationFileRegistry:
    def __init__(self):
        self.pm = pluggy.PluginManager("migration_file")
        self.pm.add_hookspecs(MigrationFileSpec)
        self.pm.load_setuptools_entrypoints("migration_file")

    def register_plugin(self, plugin):
        self.pm.register(plugin)

