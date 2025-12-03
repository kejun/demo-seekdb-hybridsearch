import pyseekdb
from pyseekdb import HNSWConfiguration, DefaultEmbeddingFunction
from typing import Optional


class DatabaseClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 2881,
                 tenant: str = "sys", user: str = "root"):
        self.host = host
        self.port = port
        self.tenant = tenant
        self.user = user
        self.client: Optional[pyseekdb.Client] = None
        self.admin: Optional[pyseekdb.AdminClient] = None

    def create_database_if_not_exists(self, database_name: str) -> bool:
        try:
            self.admin = pyseekdb.AdminClient(
                host=self.host,
                port=self.port,
                tenant=self.tenant,
                user=self.user
            )
            self.admin.create_database(database_name)
            return True
        except Exception as e:
            if "exists" in str(e).lower():
                return True
            return False

    def connect(self, database_name: str) -> bool:
        try:
            self.client = pyseekdb.Client(
                host=self.host,
                port=self.port,
                tenant=self.tenant,
                database=database_name,
                user=self.user
            )
            return True
        except Exception:
            return False

    def get_or_create_collection(self, collection_name: str,
                                 recreate: bool = False,
                                 dimension: int = 384,
                                 distance: str = "cosine",
                                 embedding_function=None):
        if not self.client:
            raise RuntimeError("Database client not connected. Call connect() first.")

        if recreate:
            try:
                self.client.delete_collection(collection_name)
            except:
                pass

        configuration = HNSWConfiguration(
            dimension=dimension,
            distance=distance
        )

        if embedding_function is None:
            embedding_function = DefaultEmbeddingFunction()

        return self.client.get_or_create_collection(
            name=collection_name,
            configuration=configuration,
            embedding_function=embedding_function
        )

