from pathlib import Path
from simply_migrate.plugins.specs import RemoteMigrationFilePlugin
from simply_migrate.logging.logger import ContextLogger


class GCSMigrationFilePlugin(RemoteMigrationFilePlugin):
    """
    Bulk-syncs scripts from Google Cloud Storage.
    Requires: pip install google-cloud-storage
    """

    def __init__(self, bucket: str, project: str | None = None):
        super().__init__()
        self.bucket = bucket
        self.project = project

    def _client(self):
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError(
                "google-cloud-storage is required for GCS script loading. "
                "Install it with: pip install google-cloud-storage"
            )
        return storage.Client(project=self.project)

    def _sync(
        self,
        path: str,
        directory: str,
        local_dir: Path,
        logger: ContextLogger,
    ) -> bool:
        client = self._client()
        prefix = f"{path.strip('/')}/{directory}/".lstrip("/")

        logger.info(f"Listing gs://{self.bucket}/{prefix}")

        try:
            bucket = client.bucket(self.bucket)
            blobs = [
                b for b in client.list_blobs(bucket, prefix=prefix)
                if b.name.endswith(".sql")
            ]
        except Exception as e:
            logger.error(f"Failed to list gs://{self.bucket}/{prefix}: {e}")
            return False

        if not blobs:
            logger.warning(f"No .sql files found at gs://{self.bucket}/{prefix}")
            return True

        logger.info(f"Downloading {len(blobs)} script(s) from GCS")

        for blob in blobs:
            relative = blob.name[len(prefix):]
            dest = local_dir / directory / relative
            dest.parent.mkdir(parents=True, exist_ok=True)

            try:
                blob.download_to_filename(str(dest))
                logger.info(f"Downloaded: {relative}")
            except Exception as e:
                logger.error(f"Failed to download {blob.name}: {e}")
                return False

        return True