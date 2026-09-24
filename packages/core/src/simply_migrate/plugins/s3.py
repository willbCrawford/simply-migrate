from pathlib import Path
from simply_migrate.plugins.specs import RemoteMigrationFilePlugin
from simply_migrate.logging.logger import ContextLogger


class S3MigrationFilePlugin(RemoteMigrationFilePlugin):
    """
    Bulk-syncs scripts from S3 to a local temp directory using a single
    paginated ListObjectsV2 + parallel GetObject calls.
    No per-file API calls during parsing.
    """

    def __init__(self, bucket: str, region: str = "us-east-1"):
        super().__init__()
        self.bucket = bucket
        self.region = region

    def _client(self):
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 script loading. "
                "Install it with: pip install boto3"
            )
        return boto3.client("s3", region_name=self.region)

    def _sync(
        self,
        path: str,
        directory: str,
        local_dir: Path,
        logger: ContextLogger,
    ) -> bool:
        s3 = self._client()
        prefix = f"{path.strip('/')}/{directory}/".lstrip("/")

        logger.info(f"Listing s3://{self.bucket}/{prefix}")

        try:
            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
            objects = [
                obj
                for page in pages
                for obj in page.get("Contents", [])
                if obj["Key"].endswith(".sql")
            ]
        except Exception as e:
            logger.error(f"Failed to list s3://{self.bucket}/{prefix}: {e}")
            return False

        if not objects:
            logger.warning(f"No .sql files found at s3://{self.bucket}/{prefix}")
            return True     # not an error — validator will warn about empty dir

        logger.info(f"Downloading {len(objects)} script(s) from S3")

        for obj in objects:
            key = obj["Key"]
            relative = key[len(prefix):]            # strip the prefix
            dest = local_dir / directory / relative
            dest.parent.mkdir(parents=True, exist_ok=True)

            try:
                s3.download_file(self.bucket, key, str(dest))
                logger.info(f"Downloaded: {relative}")
            except Exception as e:
                logger.error(f"Failed to download {key}: {e}")
                return False

        return True