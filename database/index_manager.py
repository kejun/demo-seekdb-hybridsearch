"""
索引管理器模块

使用 pyseekdb SDK 管理向量数据库集合的索引。
- HNSW 向量索引：通过 HNSWConfiguration 在创建集合时配置
- 元数据索引：通过 pymysql + SQL DDL 创建
"""
import pyseekdb
import pymysql
from pyseekdb import HNSWConfiguration, DefaultEmbeddingFunction
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class IndexManager:
    """
    索引管理器类

    通过 pyseekdb SDK 管理向量集合的创建和 HNSW 索引配置。
    通过 pymysql + SQL DDL 创建元数据字段索引。
    """

    # 默认 HNSW 索引参数
    DEFAULT_DIMENSION = 384
    DEFAULT_DISTANCE = "cosine"
    DEFAULT_M = 16
    DEFAULT_EF_CONSTRUCTION = 200

    # 元数据字段类型映射表
    FIELD_TYPES = {
        'genre': 'VARCHAR(100)',
        'author': 'VARCHAR(200)',
        'year': 'INT',
        'user_rating': 'FLOAT',
        'reviews': 'INT',
        'price': 'FLOAT',
        'name': 'VARCHAR(500)'
    }
    DEFAULT_INDEX_FIELDS = ['genre', 'year', 'user_rating', 'author']

    def __init__(self, client: pyseekdb.Client, host: str = "127.0.0.1", port: int = 2881,
                 user: str = "root", password: str = "", database: str = ""):
        """
        初始化索引管理器

        Args:
            client: pyseekdb 客户端实例
            host: SeekDB 服务器地址（用于 SQL 连接），默认 127.0.0.1
            port: SeekDB 服务器端口，默认 2881
            user: 数据库用户名，默认 root
            password: 数据库密码，默认空字符串
            database: 数据库名称
        """
        self.client = client
        self.host, self.port = host, port
        self.user, self.password, self.database = user, password, database
        self._sql_conn = None

    def create_collection_with_index(self, collection_name: str, dimension: int = DEFAULT_DIMENSION,
            distance: str = DEFAULT_DISTANCE, m: int = DEFAULT_M,
            ef_construction: int = DEFAULT_EF_CONSTRUCTION,
            embedding_function: Optional[Any] = None, recreate: bool = False) -> Any:
        """
        创建带有 HNSW 索引的向量集合

        Args:
            collection_name: 集合名称
            dimension: 向量维度，默认 384
            distance: 距离度量方式，可选 "cosine"、"l2"、"ip"，默认 "cosine"
            m: HNSW 参数，控制每个节点的最大连接数，默认 16
            ef_construction: HNSW 构建参数，控制构建时的搜索范围，默认 200
            embedding_function: 嵌入函数，None 时使用 DefaultEmbeddingFunction
            recreate: 是否重建集合，默认 False

        Returns:
            Collection: 创建的集合对象
        """
        if recreate:
            self.delete_collection(collection_name)

        return self.client.get_or_create_collection(
            name=collection_name,
            configuration=HNSWConfiguration(dimension=dimension, distance=distance, m=m, ef_construction=ef_construction),
            embedding_function=embedding_function or DefaultEmbeddingFunction()
        )

    def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception:
            return False

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            return [c.name for c in self.client.list_collections()]
        except Exception:
            return []

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息，包含名称和文档数量"""
        try:
            return {"name": collection_name, "count": self.client.get_collection(collection_name).count()}
        except Exception:
            return {"name": collection_name, "count": 0, "error": "集合不存在或无法访问"}

    # 以下代码说：引入 pymysql 是为了通过 SQL DDL 操作底层数据库表，实现对元数据列的生成和索引管理，提升基于元数据的混合检索性能。
    # seekdb 暂时不支持对元数据列创建索引。

    def _get_sql_connection(self):
        """获取 SQL 数据库连接（单例模式）"""
        if self._sql_conn is None or not self._sql_conn.open:
            self._sql_conn = pymysql.connect(
                host=self.host, port=self.port, user=self.user,
                password=self.password, database=self.database, charset='utf8mb4')
        return self._sql_conn

    @contextmanager
    def _cursor(self):
        """获取数据库游标的上下文管理器"""
        conn = self._get_sql_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        finally:
            cursor.close()

    def _execute_sql(self, sql: str, fetch: bool = False) -> Any:
        """执行 SQL 语句"""
        try:
            with self._cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchone() if fetch else True
        except Exception:
            return None if fetch else False

    def close(self):
        """关闭 SQL 连接"""
        if self._sql_conn and self._sql_conn.open:
            self._sql_conn.close()
            self._sql_conn = None

    def get_table_name(self, collection_name: str) -> str:
        """获取集合对应的数据库表名"""
        return f"c$v1${collection_name}"

    def create_metadata_indexes(self, collection_name: str, fields: Optional[List[str]] = None) -> bool:
        """
        为集合的元数据字段创建索引（通过 SQL DDL）

        为指定的元数据字段创建生成列和索引，提升混合搜索的过滤性能。

        Args:
            collection_name: 集合名称
            fields: 需要创建索引的字段列表，None 时使用默认字段

        Returns:
            bool: 至少成功创建一个索引返回 True
        """
        table_name = self.get_table_name(collection_name)
        return sum(self._create_field_index(table_name, collection_name, f)
                   for f in (fields or self.DEFAULT_INDEX_FIELDS)) > 0

    def _create_field_index(self, table_name: str, collection_name: str, field: str) -> bool:
        """为单个字段创建生成列和索引"""
        index_name = f"idx_metadata_{field}"
        if self.index_exists(collection_name, index_name):
            return True

        field_type = self.FIELD_TYPES.get(field, 'VARCHAR(255)')
        gen_column = f"gen_{field}"
        gen_expr = f"metadata->'$.{field}'" if field_type.startswith('VARCHAR') else f"metadata->>'$.{field}'"

        # 创建生成列（忽略已存在错误）
        self._execute_sql(f"ALTER TABLE {table_name} ADD COLUMN {gen_column} {field_type} GENERATED ALWAYS AS ({gen_expr})")
        # 创建索引
        return self._execute_sql(f"CREATE INDEX {index_name} ON {table_name}({gen_column})") or self.index_exists(collection_name, index_name)

    def index_exists(self, collection_name: str, index_name: str) -> bool:
        """检查索引是否存在"""
        result = self._execute_sql(
            f"SELECT COUNT(*) FROM information_schema.statistics "
            f"WHERE table_schema = DATABASE() AND table_name = '{self.get_table_name(collection_name)}' "
            f"AND index_name = '{index_name}'", fetch=True)
        return result[0] > 0 if result else False

    def list_indexes(self, collection_name: str) -> List[Dict[str, str]]:
        """列出集合的所有索引"""
        try:
            with self._cursor() as cursor:
                cursor.execute(
                    f"SELECT index_name, column_name FROM information_schema.statistics "
                    f"WHERE table_schema = DATABASE() AND table_name = '{self.get_table_name(collection_name)}'")
                return [{'name': row[0], 'column': row[1]} for row in cursor.fetchall()]
        except Exception:
            return []
