from pathlib import Path
from simply_migrate.plugins.specs import RemoteMigrationFilePlugin
from simply_migrate.logging.logger import ContextLogger


class AzureMigrationFilePlugin(RemoteMigrationFilePlugin):
    """
    Bulk-syncs scripts from Azure Blob Storage.
    Requires: pip install azure-storage-blob
    """

    def __init__(self, account_url: str, container: str):
        super().__init__()
        self.account_url = account_url
        self.container = container

    def _client(self):
        try:
            from azure.storage.blob import ContainerClient
        except ImportError:
            raise ImportError(
                "azure-storage-blob is required for Azure script loading. "
                "Install it with: pip install azure-storage-blob"
            )
        return ContainerClient(
            account_url=self.account_url,
            container_name=self.container,
        )

    def _sync(
        self,
        path: str,
        directory: str,
        local_dir: Path,
        logger: ContextLogger,
    ) -> bool:
        client = self._client()
        prefix = f"{path.strip('/')}/{directory}/".lstrip("/")

        logger.info(
            f"Listing az://{self.container}/{prefix}"
        )

        try:
            blobs = [
                b for b in client.list_blobs(name_starts_with=prefix)
                if b.name.endswith(".sql")
            ]
        except Exception as e:
            logger.error(f"Failed to list az://{self.container}/{prefix}: {e}")
            return False

        if not blobs:
            logger.warning(f"No .sql files found at az://{self.container}/{prefix}")
            return True

        logger.info(f"Downloading {len(blobs)} script(s) from Azure")

        for blob in blobs:
            relative = blob.name[len(prefix):]
            dest = local_dir / directory / relative
            dest.parent.mkdir(parents=True, exist_ok=True)

            try:
                blob_client = client.get_blob_client(blob.name)
                with open(dest, "wb") as f:
                    f.write(blob_client.download_blob().readall())
                logger.info(f"Downloaded: {relative}")
            except Exception as e:
                logger.error(f"Failed to download {blob.name}: {e}")
                return False

        return True