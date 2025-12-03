import sys
from unittest.mock import MagicMock

sys.modules["pylibseekdb"] = MagicMock()

import pyseekdb

def main():
    client = pyseekdb.Client(
        host="127.0.0.1",
        port=2881,
        tenant="sys",
        database="demo_books",
        user="root"
    )

    collection_name = "book_info"
    collection = client.get_collection(collection_name)
    query_texts = ["self improvement motivation success"]
    print(f"\n=== 语义搜索 ===")
    print(f"Query: {query_texts}")
    results = collection.query(
        query_texts=query_texts,
        n_results=5,
        include=["metadatas", "documents", "distances"]
    )
    print_results(results, "语义搜索")
    query_params = {
        "where_document": {"$contains": "inspirational"},
        "where": {"user_rating": {"$gte": 4.5}},
        "n_results": 5
    }
    knn_params = {
        "query_texts": ["inspirational life advice"],
        "where": {"user_rating": {"$gte": 4.5}},
        "n_results": 5
    }
    print(f"\n=== 混合搜索 (评分≥4.5) ===")
    print(f"Query: {query_params}")
    print(f"KNN Query Texts: {knn_params['query_texts']}")
    results = collection.hybrid_search(
        query=query_params,
        knn=knn_params,
        rank={"rrf": {}},
        n_results=5,
        include=["metadatas", "documents", "distances"]
    )
    print_results(results, "混合搜索 (评分≥4.5)")
    query_params = {
        "where_document": {"$contains": "business"},
        "where": {"genre": "Non Fiction"},
        "n_results": 5
    }
    knn_params = {
        "query_texts": ["business entrepreneurship leadership"],
        "where": {"genre": "Non Fiction"},
        "n_results": 5
    }
    print(f"\n=== 混合搜索 (Non Fiction) ===")
    print(f"Query: {query_params}")
    print(f"KNN Query Texts: {knn_params['query_texts']}")
    results = collection.hybrid_search(
        query=query_params,
        knn=knn_params,
        rank={"rrf": {}},
        n_results=5,
        include=["metadatas", "documents", "distances"]
    )
    print_results(results, "混合搜索 (Non Fiction)")
    where_condition = {
        "$and": [
            {"year": {"$gte": 2015}},
            {"user_rating": {"$gte": 4.0}},
            {"genre": "Fiction"}
        ]
    }
    query_params = {
        "where_document": {"$contains": "fiction"},
        "where": where_condition,
        "n_results": 5
    }
    knn_params = {
        "query_texts": ["fiction story novel"],
        "where": where_condition,
        "n_results": 5
    }
    print(f"\n=== 混合搜索 (Fiction, 2015年后, 评分≥4.0) ===")
    print(f"Query: {query_params}")
    print(f"KNN Query Texts: {knn_params['query_texts']}")
    results = collection.hybrid_search(
        query=query_params,
        knn=knn_params,
        rank={"rrf": {}},
        n_results=5,
        include=["metadatas", "documents", "distances"]
    )
    print_results(results, "混合搜索 (Fiction, 2015年后, 评分≥4.0)")
    query_params = {
        "where_document": {"$contains": "popular"},
        "where": {"reviews": {"$gte": 10000}},
        "n_results": 10
    }
    knn_params = {
        "query_texts": ["popular bestseller"],
        "where": {"reviews": {"$gte": 10000}},
        "n_results": 10
    }
    print(f"\n=== 混合搜索 (评论数≥10000) ===")
    print(f"Query: {query_params}")
    print(f"KNN Query Texts: {knn_params['query_texts']}")
    results = collection.hybrid_search(
        query=query_params,
        knn=knn_params,
        rank={"rrf": {}},
        n_results=10,
        include=["metadatas", "documents", "distances"]
    )
    print_results(results, "混合搜索 (评论数≥10000)")
    where_condition = {
        "$and": [
            {"price": {"$gte": 5}},
            {"price": {"$lte": 15}},
            {"user_rating": {"$gte": 4.5}}
        ]
    }
    query_params = {
        "where_document": {"$contains": "good book"},
        "where": where_condition,
        "n_results": 5
    }
    knn_params = {
        "query_texts": ["good book recommendation"],
        "where": where_condition,
        "n_results": 5
    }
    print(f"\n=== 混合搜索 ($5-$15, 评分≥4.5) ===")
    print(f"Query: {query_params}")
    print(f"KNN Query Texts: {knn_params['query_texts']}")
    results = collection.hybrid_search(
        query=query_params,
        knn=knn_params,
        rank={"rrf": {}},
        n_results=5,
        include=["metadatas", "documents", "distances"]
    )
    print_results(results, "混合搜索 ($5-$15, 评分≥4.5)")


def print_results(results, search_type):
    if not results.get('ids') or not results['ids'][0]:
        print(f"没有找到匹配的结果")
        return

    # 获取所有数据
    ids = results['ids'][0]
    metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else []
    distances = results.get('distances', [[]])[0] if results.get('distances') else []

    # 创建索引列表，并根据距离值排序（距离小的在前）
    indices = list(range(len(ids)))

    def get_distance_value(idx):
        """获取距离值用于排序，如果不存在或无效则返回无穷大"""
        try:
            if idx < len(distances) and distances[idx] is not None:
                return float(distances[idx])
        except (ValueError, TypeError, IndexError):
            pass
        return float('inf')  # 没有距离值的排在最后

    # 按距离值排序索引
    indices.sort(key=get_distance_value)

    print(f"\n{search_type} - 找到 {len(ids)} 条结果:\n")

    for rank, i in enumerate(indices, 1):
        doc_meta = metadatas[i] if i < len(metadatas) else {}

        # 获取距离值
        try:
            distance = distances[i] if i < len(distances) else None
        except (IndexError, KeyError, TypeError):
            distance = None

        # 根据距离计算相似度 (假设使用余弦距离，相似度 = 1 - 距离)
        if distance is not None:
            # 确保distance是数值类型
            try:
                distance_float = float(distance)
                similarity = 1 - distance_float
                similarity_str = f"{similarity:.4f}"
                distance_str = f"{distance_float:.4f}"
            except (ValueError, TypeError):
                similarity_str = "N/A"
                distance_str = str(distance) if distance else "N/A"
        else:
            similarity_str = "N/A"
            distance_str = "N/A"

        print(f"[{rank}] {doc_meta.get('name', 'Unknown')}")
        print(f"    作者: {doc_meta.get('author', 'Unknown')}")
        print(f"    评分: {doc_meta.get('user_rating', 'N/A')}")
        print(f"    评论数: {doc_meta.get('reviews', 'N/A')}")
        print(f"    价格: ${doc_meta.get('price', 'N/A')}")
        print(f"    年份: {doc_meta.get('year', 'N/A')}")
        print(f"    类型: {doc_meta.get('genre', 'N/A')}")
        print(f"    相似度距离: {distance_str}")
        print(f"    相似度: {similarity_str}")
        print()


if __name__ == "__main__":
    main()
