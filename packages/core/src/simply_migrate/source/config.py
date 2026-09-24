from pathlib import Path

import yaml

from simply_migrate.models.models import SourceConfig, SourceType


class SourceConfigError(ValueError):
    pass


def load_source_config(path: Path) -> SourceConfig:
    """
    Load and validate the source block from tenants.yaml.
    Defaults to local if no source block is defined.
    """
    with path.open() as f:
        raw = yaml.safe_load(f)

    source_block = raw.get("source", {})
    source_type_raw = source_block.get("type", "local")

    try:
        source_type = SourceType(source_type_raw)
    except ValueError:
        valid = [t.value for t in SourceType]
        raise SourceConfigError(
            f"Invalid source type {source_type_raw!r}. "
            f"Must be one of: {valid}"
        )

    config = SourceConfig(
        type=source_type,
        options={k: v for k, v in source_block.items() if k != "type"},
    )

    _validate_source_config(config)

    return config


def _validate_source_config(config: SourceConfig) -> None:
    if config.type == SourceType.S3:
        if not config.bucket:
            raise SourceConfigError("S3 source requires 'bucket' to be set.")

    elif config.type == SourceType.GCS:
        if not config.bucket:
            raise SourceConfigError("GCS source requires 'bucket' to be set.")

    elif config.type == SourceType.AZURE:
        if not config.account_url:
            raise SourceConfigError("Azure source requires 'account_url' to be set.")
        if not config.container:
            raise SourceConfigError("Azure source requires 'container' to be set.")
