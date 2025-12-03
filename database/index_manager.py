import pyseekdb
from typing import Optional, List, Dict

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


class IndexManager:
    def __init__(self, client: pyseekdb.Client,
                 host: str = "127.0.0.1",
                 port: int = 2881,
                 tenant: str = "sys",
                 user: str = "root",
                 password: str = "",
                 database: str = ""):
        self.client = client
        self.host = host
        self.port = port
        self.tenant = tenant
        self.user = user
        self.password = password
        self.database = database
        self._mysql_conn = None

    def _get_mysql_connection(self):
        if not PYMYSQL_AVAILABLE:
            raise RuntimeError("pymysql is not available. Please install it: pip install pymysql")

        if self._mysql_conn is None or not self._mysql_conn.open:
            self._mysql_conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4'
            )
        return self._mysql_conn

    def _execute_sql(self, sql: str) -> bool:
        try:
            conn = self._get_mysql_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql)
                conn.commit()
            return True
        except Exception:
            return False

    def close(self):
        if self._mysql_conn and self._mysql_conn.open:
            self._mysql_conn.close()
            self._mysql_conn = None

    def get_table_name(self, collection_name: str) -> str:
        return f"c$v1${collection_name}"

    def create_metadata_indexes(self, collection_name: str,
                               fields: Optional[List[str]] = None) -> bool:
        if fields is None:
            fields = ['genre', 'year', 'user_rating', 'author']

        table_name = self.get_table_name(collection_name)

        field_types = {
            'genre': 'VARCHAR(100)',
            'author': 'VARCHAR(200)',
            'year': 'INT',
            'user_rating': 'FLOAT',
            'reviews': 'INT',
            'price': 'FLOAT',
            'name': 'VARCHAR(500)'
        }

        success_count = 0
        for field in fields:
            try:
                index_name = f"idx_metadata_{field}"
                field_type = field_types.get(field, 'VARCHAR(255)')

                if self.index_exists(collection_name, index_name):
                    continue

                generated_column_name = f"gen_{field}"

                if field_type.startswith('VARCHAR'):
                    generated_expr = f"metadata->'$.{field}'"
                else:
                    generated_expr = f"metadata->>'$.{field}'"

                create_column_sql = f"""
                ALTER TABLE {table_name}
                ADD COLUMN {generated_column_name} {field_type}
                GENERATED ALWAYS AS ({generated_expr})
                """

                column_created = False
                try:
                    conn = self._get_mysql_connection()
                    with conn.cursor() as cursor:
                        cursor.execute(create_column_sql)
                        conn.commit()
                        column_created = True
                except Exception as col_e:
                    error_str = str(col_e).lower()
                    if "duplicate column name" in error_str or "already exists" in error_str:
                        column_created = True

                if not column_created:
                    continue

                sql = f"""
                CREATE INDEX {index_name} ON {table_name}({generated_column_name})
                """

                if self._execute_sql(sql):
                    success_count += 1
                elif self.index_exists(collection_name, index_name):
                    success_count += 1

            except Exception:
                continue

        return success_count > 0

    def index_exists(self, collection_name: str, index_name: str) -> bool:
        table_name = self.get_table_name(collection_name)
        sql = f"""
        SELECT COUNT(*) as cnt
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
        AND table_name = '{table_name}'
        AND index_name = '{index_name}'
        """

        try:
            conn = self._get_mysql_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result[0] > 0 if result else False
        except Exception:
            return False

    def optimize_hnsw_index(self, collection_name: str,
                            m: int = 32,
                            ef_construction: int = 400) -> bool:
        table_name = self.get_table_name(collection_name)
        index_name = "idx_vec"

        sql = f"""
        DROP INDEX IF EXISTS {index_name} ON {table_name};
        CREATE INDEX {index_name} ON {table_name}(embedding)
        USING HNSW WITH (m={m}, ef_construction={ef_construction});
        """

        return self._execute_sql(sql)

    def list_indexes(self, collection_name: str) -> List[Dict[str, str]]:
        return []

