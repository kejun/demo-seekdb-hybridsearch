import sys
from unittest.mock import MagicMock

sys.modules["pylibseekdb"] = MagicMock()

import pyseekdb
import pymysql


def connect_to_database() -> tuple:
    client = pyseekdb.Client(
        host="127.0.0.1",
        port=2881,
        tenant="sys",
        database="demo_books",
        user="root"
    )

    mysql_conn = pymysql.connect(
        host="127.0.0.1",
        port=2881,
        user="root",
        password="",
        database="demo_books",
        charset='utf8mb4'
    )

    collection_name = "book_info"
    collection = client.get_collection(collection_name)

    return client, collection, mysql_conn


def test_tokenizer(mysql_conn, text: str, mode: str = "smart"):
    sql = f"""
    SELECT tokenize(%s, 'IK', '[{{"additional_args":[{{"ik_mode": "{mode}"}}]}}]')
    """

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute(sql, (text,))
            result = cursor.fetchone()
            if result and result[0]:
                tokens = result[0]
                print(f"分词结果 ({len(tokens)} 个词):")
                for i, token in enumerate(tokens, 1):
                    print(f"  {i}. {token}")
    except Exception as e:
        print(f"分词失败: {e}")


def test_fulltext_search(collection, keyword: str):
    try:
        results = collection.get(
            where_document={"$contains": keyword},
            limit=5,
            include=["metadatas", "documents"]
        )

        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        print(f"找到 {len(ids)} 条结果:")

        for i in range(min(5, len(ids))):
            meta = metadatas[i] if i < len(metadatas) else {}
            doc = documents[i] if i < len(documents) else "N/A"
            print(f"[{i+1}] {meta.get('name', 'Unknown')}")
            print(f"     作者: {meta.get('author', 'Unknown')}")
            print(f"     内容片段: {doc[:100]}..." if len(doc) > 100 else f"     内容: {doc}")

    except Exception as e:
        print(f"全文搜索失败: {e}")


def check_fulltext_index(mysql_conn, collection_name: str):
    table_name = f"c$v1${collection_name}"
    sql = f"""
    SHOW INDEX FROM {table_name} WHERE Key_name = 'idx_fts'
    """

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()
            if results:
                print("全文索引存在:")
                for row in results:
                    print(f"  索引名: {row[2]}")
                    print(f"  列名: {row[4]}")
                    print(f"  索引类型: {row[10]}")
                    if len(row) > 11:
                        print(f"  其他信息: {row[11:]}")
    except Exception as e:
        print(f"检查索引失败: {e}")


def main():
    try:
        client, collection, mysql_conn = connect_to_database()
    except Exception as e:
        print(f"无法连接到数据库: {e}")
        return

    check_fulltext_index(mysql_conn, "book_info")

    test_tokenizer(mysql_conn, "南京市长江大桥有1千米长", mode="smart")
    test_tokenizer(mysql_conn, "南京市长江大桥有1千米长", mode="max_word")

    test_tokenizer(mysql_conn, "Business 商业 书籍推荐", mode="smart")
    test_tokenizer(mysql_conn, "详见WWW.XXX.COM, 邮箱xx@OB.COM 192.168.1.1", mode="smart")

    test_fulltext_search(collection, "Business 商业 书籍推荐")
    test_fulltext_search(collection, "Education")
    test_fulltext_search(collection, "Health")

    test_fulltext_search(collection, "商业")
    test_fulltext_search(collection, "教育")

    mysql_conn.close()


if __name__ == "__main__":
    main()

