"""
索引管理器模块

用于管理向量数据库集合的元数据索引和向量索引。
支持为 JSON 元数据字段创建生成列和索引，以及优化 HNSW 向量索引。
"""
import pyseekdb
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


class IndexManager:
    """
    索引管理器类

    负责管理向量数据库集合的索引创建和维护。
    通过 SeekDB 连接为元数据字段创建生成列和索引，提升查询性能。
    """

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

    # 默认需要创建索引的字段列表
    DEFAULT_FIELDS = ['genre', 'year', 'user_rating', 'author']

    def __init__(self, client: pyseekdb.Client,
                 host: str = "127.0.0.1",
                 port: int = 2881,
                 tenant: str = "sys",
                 user: str = "root",
                 password: str = "",
                 database: str = ""):
        """
        初始化索引管理器

        Args:
            client: pyseekdb 客户端实例
            host: SeekDB 服务器地址，默认 127.0.0.1
            port: SeekDB 服务器端口，默认 2881
            tenant: 租户名称，默认 sys
            user: 数据库用户名，默认 root
            password: 数据库密码，默认空字符串
            database: 数据库名称
        """
        self.client = client
        self.host = host
        self.port = port
        self.tenant = tenant
        self.user = user
        self.password = password
        self.database = database
        self._seekdb_conn = None  # SeekDB 连接对象，延迟初始化

    def _get_seekdb_connection(self):
        """
        获取 SeekDB 数据库连接（单例模式）

        Returns:
            pymysql.Connection: SeekDB 连接对象

        Raises:
            RuntimeError: 当数据库连接库未安装时抛出异常
        """
        if not PYMYSQL_AVAILABLE:
            raise RuntimeError("数据库连接库未安装，请安装: pip install pymysql")
        # 如果连接不存在或已关闭，创建新连接
        if self._seekdb_conn is None or not self._seekdb_conn.open:
            self._seekdb_conn = pymysql.connect(
                host=self.host, port=self.port, user=self.user,
                password=self.password, database=self.database, charset='utf8mb4'
            )
        return self._seekdb_conn

    @contextmanager
    def _cursor(self):
        """
        数据库游标上下文管理器

        自动处理游标的创建、事务提交和资源释放。

        Yields:
            pymysql.cursors.Cursor: 数据库游标对象
        """
        conn = self._get_seekdb_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()  # 自动提交事务
        finally:
            cursor.close()  # 确保游标被关闭

    def _execute_sql(self, sql: str, fetch: bool = False) -> Any:
        """
        执行 SQL 语句的通用方法

        Args:
            sql: 要执行的 SQL 语句
            fetch: 是否返回查询结果，False 表示执行更新操作

        Returns:
            当 fetch=True 时返回查询结果的第一行，否则返回 True/False
            执行失败时返回 None（fetch=True）或 False（fetch=False）
        """
        try:
            with self._cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchone() if fetch else True
        except Exception:
            return None if fetch else False

    def close(self):
        if self._seekdb_conn and self._seekdb_conn.open:
            self._seekdb_conn.close()
            self._seekdb_conn = None

    def get_table_name(self, collection_name: str) -> str:
        """
        根据集合名称获取对应的数据库表名

        Args:
            collection_name: 集合名称

        Returns:
            数据库表名，格式为 c$v1${collection_name}
        """
        return f"c$v1${collection_name}"

    def create_metadata_indexes(self, collection_name: str,
                               fields: Optional[List[str]] = None) -> bool:
        """
        为集合的元数据字段创建索引

        为指定的元数据字段创建生成列和索引，提升基于元数据的查询性能。
        如果字段未指定，则使用默认字段列表。

        Args:
            collection_name: 集合名称
            fields: 需要创建索引的字段列表，None 时使用默认字段

        Returns:
            bool: 至少成功创建一个索引返回 True，否则返回 False
        """
        fields = fields or self.DEFAULT_FIELDS
        table_name = self.get_table_name(collection_name)
        success_count = 0

        for field in fields:
            if self._create_field_index(table_name, collection_name, field):
                success_count += 1

        return success_count > 0

    def _create_field_index(self, table_name: str, collection_name: str, field: str) -> bool:
        """
        为单个字段创建索引（内部方法）

        流程：
        1. 检查索引是否已存在
        2. 创建生成列（从 JSON 元数据中提取字段值）
        3. 在生成列上创建索引

        Args:
            table_name: 数据库表名
            collection_name: 集合名称（用于检查索引是否存在）
            field: 字段名称

        Returns:
            bool: 索引创建成功返回 True，否则返回 False
        """
        index_name = f"idx_metadata_{field}"
        # 如果索引已存在，直接返回成功
        if self.index_exists(collection_name, index_name):
            return True

        field_type = self.FIELD_TYPES.get(field, 'VARCHAR(255)')
        generated_column_name = f"gen_{field}"
        # VARCHAR 类型使用 -> 操作符，其他类型使用 ->> 操作符（返回文本）
        generated_expr = f"metadata->'$.{field}'" if field_type.startswith('VARCHAR') else f"metadata->>'$.{field}'"

        # 创建生成列：从 JSON 元数据中自动提取字段值
        create_column_sql = (
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {generated_column_name} {field_type} "
            f"GENERATED ALWAYS AS ({generated_expr})"
        )

        try:
            with self._cursor() as cursor:
                cursor.execute(create_column_sql)
        except Exception as e:
            # 如果列已存在，忽略错误继续执行
            error_str = str(e).lower()
            if "duplicate column name" not in error_str and "already exists" not in error_str:
                return False

        # 在生成列上创建索引
        create_index_sql = f"CREATE INDEX {index_name} ON {table_name}({generated_column_name})"
        return self._execute_sql(create_index_sql) or self.index_exists(collection_name, index_name)

    def index_exists(self, collection_name: str, index_name: str) -> bool:
        """
        检查指定索引是否存在

        Args:
            collection_name: 集合名称
            index_name: 索引名称

        Returns:
            bool: 索引存在返回 True，否则返回 False
        """
        table_name = self.get_table_name(collection_name)
        sql = (
            f"SELECT COUNT(*) FROM information_schema.statistics "
            f"WHERE table_schema = DATABASE() "
            f"AND table_name = '{table_name}' AND index_name = '{index_name}'"
        )
        result = self._execute_sql(sql, fetch=True)
        return result[0] > 0 if result else False

    def optimize_hnsw_index(self, collection_name: str,
                            m: int = 32,
                            ef_construction: int = 400) -> bool:
        """
        优化或重建 HNSW 向量索引

        HNSW (Hierarchical Navigable Small World) 是一种高效的向量相似度搜索索引。
        此方法会先删除现有索引（如果存在），然后使用新参数重新创建。

        Args:
            collection_name: 集合名称
            m: HNSW 参数，控制每个节点的最大连接数，默认 32
            ef_construction: HNSW 构建参数，控制构建时的搜索范围，默认 400

        Returns:
            bool: 索引创建成功返回 True，否则返回 False

        Note:
            - m 值越大，索引质量越好但构建时间越长
            - ef_construction 值越大，索引质量越好但构建时间越长
        """
        table_name = self.get_table_name(collection_name)
        index_name = "idx_vec"
        sql = (
            f"DROP INDEX IF EXISTS {index_name} ON {table_name}; "
            f"CREATE INDEX {index_name} ON {table_name}(embedding) "
            f"USING HNSW WITH (m={m}, ef_construction={ef_construction})"
        )
        return self._execute_sql(sql)

    def list_indexes(self, collection_name: str) -> List[Dict[str, str]]:
        """
        列出集合的所有索引

        Args:
            collection_name: 集合名称

        Returns:
            List[Dict[str, str]]: 索引列表，每个元素包含 'name'（索引名）和 'column'（列名）
            查询失败时返回空列表
        """
        table_name = self.get_table_name(collection_name)
        sql = (
            f"SELECT index_name, column_name FROM information_schema.statistics "
            f"WHERE table_schema = DATABASE() AND table_name = '{table_name}'"
        )
        try:
            with self._cursor() as cursor:
                cursor.execute(sql)
                return [{'name': row[0], 'column': row[1]} for row in cursor.fetchall()]
        except Exception:
            return []

