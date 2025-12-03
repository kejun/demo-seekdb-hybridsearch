import sys
from unittest.mock import MagicMock
import time

sys.modules["pylibseekdb"] = MagicMock()

import pandas as pd
from tqdm import tqdm
from database.db_client import DatabaseClient
from database.index_manager import IndexManager
from data.processor import DataProcessor


def load_data(csv_path: str) -> pd.DataFrame:
    print(f"\n正在加载数据文件: {csv_path}")

    start_time = time.time()
    df = pd.read_csv(csv_path)
    load_time = time.time() - start_time

    print(f"数据加载完成!")
    print(f"   - 总行数: {len(df):,}")
    print(f"   - 总列数: {len(df.columns)}")
    print(f"   - 列名: {', '.join(df.columns.tolist())}")
    print(f"   - 加载耗时: {load_time:.2f} 秒")
    print()

    return df


def query_collection(collection, query_text: str, n_results: int = 3):
    print(f"\n执行查询: \"{query_text}\"")

    start_time = time.time()
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    query_time = time.time() - start_time

    result_count = len(results['ids'][0]) if results['ids'] else 0
    print(f"查询完成! 找到 {result_count} 条结果 (耗时: {query_time:.3f} 秒)\n")

    for i in range(result_count):
        doc_id = results['ids'][0][i]
        doc_text = results['documents'][0][i]
        doc_meta = results['metadatas'][0][i]
        distance = results['distances'][0][i] if 'distances' in results else "N/A"
        similarity = 1 - distance if isinstance(distance, (int, float)) else "N/A"
        similarity_pct = f"{similarity * 100:.2f}%" if isinstance(similarity, (int, float)) else "N/A"

        print(f"结果 #{i+1} (相似度: {similarity_pct})")
        print(f"  ID: {doc_id}")
        print(f"  书名: {doc_meta.get('name', 'N/A')}")
        print(f"  作者: {doc_meta.get('author', 'N/A')}")
        print(f"  评分: {doc_meta.get('user_rating', 'N/A')}")
        print(f"  类型: {doc_meta.get('genre', 'N/A')}")
        print(f"  年份: {doc_meta.get('year', 'N/A')}")
        print(f"  价格: ${doc_meta.get('price', 'N/A')}")
        reviews = doc_meta.get('reviews', 'N/A')
        if isinstance(reviews, (int, float)):
            print(f"  评论数: {reviews:,.0f}")
        else:
            print(f"  评论数: {reviews}")
        print(f"  内容片段: {doc_text[:150]}...")
        print(f"  距离值: {distance}")
        print()

    print()


def main():
    total_start_time = time.time()

    csv_path = 'bestsellers_with_categories.csv'
    database_name = "demo_books"
    collection_name = "book_info"

    # 1. 加载数据
    df = load_data(csv_path)

    # 2. 连接数据库
    print(f"\n正在连接数据库...")
    print(f"  主机: 127.0.0.1:2881")
    print(f"  数据库: {database_name}")
    print(f"  集合: {collection_name}")

    db_client = DatabaseClient(
        host="127.0.0.1",
        port=2881,
        tenant="sys",
        user="root"
    )

    if not db_client.create_database_if_not_exists(database_name):
        print("数据库创建失败!")
        return
    print("数据库已就绪")

    if not db_client.connect(database_name):
        print("数据库连接失败!")
        return
    print("数据库连接成功")
    print()

    # 3. 创建集合
    print(f"\n正在创建/重建集合...")
    print(f"  集合名称: {collection_name}")
    print(f"  向量维度: 384")
    print(f"  距离度量: cosine")

    collection = db_client.get_or_create_collection(
        collection_name,
        recreate=True,
        dimension=384,
        distance="cosine"
    )
    print("集合创建成功")
    print()

    # 4. 处理数据
    print(f"\n正在处理数据...")

    process_start = time.time()
    processor = DataProcessor()
    ids, documents, metadatas = processor.prepare_data(df)
    process_time = time.time() - process_start

    print(f"数据预处理完成!")
    print(f"   - 总记录数: {len(ids):,}")
    print(f"   - 验证错误数: {processor.validation_errors}")
    print(f"   - 处理耗时: {process_time:.2f} 秒")
    print()

    # 5. 导入数据到集合
    print(f"\n正在导入数据到集合...")

    import_start = time.time()
    total_batches = (len(ids) + 100 - 1) // 100
    print(f"   - 批次大小: 100")
    print(f"   - 总批次数: {total_batches}")
    print(f"   - 开始导入...\n")

    # 创建进度条
    pbar = tqdm(
        total=total_batches,
        desc="导入进度",
        unit="批次",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    )

    def progress_callback(current, total):
        pbar.update(1)
        processed_records = min(current * 100, len(ids))
        pbar.set_postfix_str(f"已处理 {processed_records}/{len(ids)} 条记录")

    processor.add_data_to_collection(
        collection,
        ids,
        documents,
        metadatas,
        batch_size=100,
        progress_callback=progress_callback
    )

    pbar.close()
    import_time = time.time() - import_start
    print(f"\n数据导入完成!")
    print(f"   - 导入耗时: {import_time:.2f} 秒")
    print(f"   - 平均速度: {len(ids) / import_time:.0f} 条/秒")
    print()

    # 6. 创建索引
    print(f"\n正在创建元数据索引...")

    index_start = time.time()
    index_manager = IndexManager(
        client=db_client.client,
        host=db_client.host,
        port=db_client.port,
        tenant=db_client.tenant,
        user=db_client.user,
        password="",
        database=database_name
    )

    index_fields = ['genre', 'year', 'user_rating', 'author', 'reviews', 'price']
    print(f"   - 索引字段: {', '.join(index_fields)}")

    success = index_manager.create_metadata_indexes(
        collection_name,
        fields=index_fields
    )

    index_time = time.time() - index_start
    index_manager.close()

    if success:
        print(f"索引创建完成!")
    else:
        print(f"索引创建可能存在问题")
    print(f"   - 创建耗时: {index_time:.2f} 秒")
    print()

    # 7. 执行测试查询
    query_text = "Self‑Improvement and Personal Development"
    query_collection(collection, query_text, n_results=3)

    # 8. 总结
    total_time = time.time() - total_start_time
    print(f"\n数据导入流程完成!")
    print(f"  总耗时: {total_time:.2f} 秒")
    print(f"  导入记录数: {len(ids):,}")
    print(f"  数据库: {database_name}")
    print(f"  集合: {collection_name}")
    print()


if __name__ == "__main__":
    main()
