import pluggy

job_hook_spec = pluggy.HookspecMarker("job")
migration_hook_spec = pluggy.HookspecMarker("migration")
migration_file_spec = pluggy.HookspecMarker("migration_file")
