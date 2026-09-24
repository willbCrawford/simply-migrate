from simply_migrate.models.models import SourceConfig, SourceType
from simply_migrate.source.base import ScriptSource


def build_script_source(config: SourceConfig) -> ScriptSource:
    """
    The only place in the codebase that knows about source types.
    Called once at CLI startup — returns a source the loaders use directly.
    """
    if config.type == SourceType.LOCAL:
        from simply_migrate.source.local import LocalScriptSource
        return LocalScriptSource()

    # if config.type == SourceType.S3:
    #     from simply_migrate.source.remote.s3 import S3ScriptSource
    #     return S3ScriptSource(
    #         bucket=config.bucket,
    #         region=config.region,
    #         path_prefix=config.path_prefix,
    #     )
    #
    # if config.type == SourceType.GCS:
    #     from simply_migrate.source.remote.gcs import GCSScriptSource
    #     return GCSScriptSource(
    #         bucket=config.bucket,
    #         project=config.project,
    #     )
    #
    # if config.type == SourceType.AZURE:
    #     from simply_migrate.source.remote.azure import AzureScriptSource
    #     return AzureScriptSource(
    #         account_url=config.account_url,
    #         container=config.container,
    #     )

    raise ValueError(f"Unhandled source type: {config.type}")