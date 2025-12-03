import sys
from unittest.mock import MagicMock

sys.modules["pylibseekdb"] = MagicMock()

import pyseekdb
import time
from typing import Dict, List, Tuple, Any
from collections import defaultdict


def connect_to_database() -> Tuple[pyseekdb.Client, Any]:
    client = pyseekdb.Client(
        host="127.0.0.1",
        port=2881,
        tenant="sys",
        database="demo_books",
        user="root"
    )

    collection_name = "book_info"
    collection = client.get_collection(collection_name)
    return client, collection


def full_text_search(collection: Any, keyword: str, limit: int = 10) -> Tuple[Dict, float]:
    start_time = time.time()
    try:
        results = collection.get(
            where_document={"$contains": keyword},
            limit=limit,
            include=["metadatas", "documents"]
        )
        elapsed_time = time.time() - start_time
        return results, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"全文搜索出错: {e}")
        return {"ids": [], "documents": [], "metadatas": []}, elapsed_time


def hybrid_search(collection: Any, keyword: str, n_results: int = 10) -> Tuple[Dict, float]:
    start_time = time.time()

    try:
        results = collection.hybrid_search(
            query={
                "where_document": {"$contains": keyword},
                "n_results": n_results
            },
            knn={
                "query_texts": [keyword],
                "n_results": n_results
            },
            rank={"rrf": {}},
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )
        elapsed_time = time.time() - start_time
        return results, elapsed_time
    except Exception as e:
        try:
            results = collection.query(
                query_texts=[keyword],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]
            )
            elapsed_time = time.time() - start_time
            return results, elapsed_time
        except Exception:
            elapsed_time = time.time() - start_time
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}, elapsed_time


def compare_results(full_text_results: Dict, hybrid_results: Dict) -> Dict[str, Any]:
    ft_ids = set(full_text_results.get("ids", []))
    hybrid_ids_list = hybrid_results.get("ids", [[]])
    hybrid_ids = set(hybrid_ids_list[0] if hybrid_ids_list else [])

    common_ids = ft_ids & hybrid_ids
    ft_only = ft_ids - hybrid_ids
    hybrid_only = hybrid_ids - ft_ids

    total_ft = len(ft_ids)
    total_hybrid = len(hybrid_ids)
    overlap_count = len(common_ids)

    overlap_ratio_ft = (overlap_count / total_ft * 100) if total_ft > 0 else 0
    overlap_ratio_hybrid = (overlap_count / total_hybrid * 100) if total_hybrid > 0 else 0

    return {
        "full_text_count": total_ft,
        "hybrid_count": total_hybrid,
        "common_count": overlap_count,
        "full_text_only": len(ft_only),
        "hybrid_only": len(hybrid_only),
        "overlap_ratio_ft": overlap_ratio_ft,
        "overlap_ratio_hybrid": overlap_ratio_hybrid,
        "common_ids": list(common_ids),
        "full_text_only_ids": list(ft_only),
        "hybrid_only_ids": list(hybrid_only)
    }


def print_query_comparison(query: str, ft_results: Dict, hybrid_results: Dict,
                          ft_time: float, hybrid_time: float, comparison: Dict):
    print("\n" + "=" * 80)
    print(f"查询: '{query}'")
    print("=" * 80)

    # 性能对比
    print("\n【性能对比】")
    print(f"  全文搜索: {ft_time*1000:.2f} ms")
    print(f"  混合搜索: {hybrid_time*1000:.2f} ms")
    speed_diff = ((hybrid_time - ft_time) / ft_time * 100) if ft_time > 0 else 0
    if speed_diff > 0:
        print(f"  全文搜索快 {speed_diff:.1f}%")
    else:
        print(f"  混合搜索快 {abs(speed_diff):.1f}%")

    # 结果数量对比
    print("\n【结果数量对比】")
    print(f"  全文搜索: {comparison['full_text_count']} 条结果")
    print(f"  混合搜索: {comparison['hybrid_count']} 条结果")

    # 重叠度分析
    print("\n【结果重叠度分析】")
    print(f"  共同结果: {comparison['common_count']} 条")
    print(f"  仅全文搜索有: {comparison['full_text_only']} 条")
    print(f"  仅混合搜索有: {comparison['hybrid_only']} 条")
    print(f"  重叠率 (相对于全文搜索): {comparison['overlap_ratio_ft']:.1f}%")
    print(f"  重叠率 (相对于混合搜索): {comparison['overlap_ratio_hybrid']:.1f}%")

    # 显示前5个结果
    print("\n【全文搜索结果 (前5个)】")
    ft_ids = ft_results.get("ids", [])
    ft_docs = ft_results.get("documents", [])
    ft_metas = ft_results.get("metadatas", [])

    for i in range(min(5, len(ft_ids))):
        meta = ft_metas[i] if i < len(ft_metas) else {}
        doc = ft_docs[i] if i < len(ft_docs) else "N/A"
        print(f"  [{i+1}] {meta.get('name', 'Unknown')} - {meta.get('author', 'Unknown')}")
        print(f"      内容: {doc[:80]}..." if len(doc) > 80 else f"      内容: {doc}")

    print("\n【混合搜索结果 (前5个)】")
    hybrid_ids_list = hybrid_results.get("ids", [[]])
    hybrid_docs_list = hybrid_results.get("documents", [[]])
    hybrid_metas_list = hybrid_results.get("metadatas", [[]])
    hybrid_distances_list = hybrid_results.get("distances", [[]])

    hybrid_ids = hybrid_ids_list[0] if hybrid_ids_list else []
    hybrid_docs = hybrid_docs_list[0] if hybrid_docs_list else []
    hybrid_metas = hybrid_metas_list[0] if hybrid_metas_list else []
    hybrid_distances = hybrid_distances_list[0] if hybrid_distances_list else []

    for i in range(min(5, len(hybrid_ids))):
        meta = hybrid_metas[i] if i < len(hybrid_metas) else {}
        doc = hybrid_docs[i] if i < len(hybrid_docs) else "N/A"
        distance = hybrid_distances[i] if i < len(hybrid_distances) else "N/A"
        print(f"  [{i+1}] {meta.get('name', 'Unknown')} - {meta.get('author', 'Unknown')}")
        print(f"      内容: {doc[:80]}..." if len(doc) > 80 else f"      内容: {doc}")
        print(f"      相似度距离: {distance:.4f}" if isinstance(distance, (int, float)) else f"      相似度距离: {distance}")


def run_performance_test(collection: Any, queries: List[str], iterations: int = 5) -> Dict[str, Any]:
    performance_stats = defaultdict(lambda: {
        "full_text_times": [],
        "hybrid_times": []
    })

    for query in queries:
        for i in range(iterations):
            _, ft_time = full_text_search(collection, query, limit=10)
            _, hybrid_time = hybrid_search(collection, query, n_results=10)
            performance_stats[query]["full_text_times"].append(ft_time)
            performance_stats[query]["hybrid_times"].append(hybrid_time)

    stats_summary = {}
    for query, times in performance_stats.items():
        ft_times = times["full_text_times"]
        hybrid_times = times["hybrid_times"]

        stats_summary[query] = {
            "full_text": {
                "avg": sum(ft_times) / len(ft_times),
                "min": min(ft_times),
                "max": max(ft_times),
                "total": sum(ft_times)
            },
            "hybrid": {
                "avg": sum(hybrid_times) / len(hybrid_times),
                "min": min(hybrid_times),
                "max": max(hybrid_times),
                "total": sum(hybrid_times)
            }
        }

    return stats_summary


def print_performance_summary(stats_summary: Dict[str, Any]):
    print("\n" + "=" * 80)
    print("性能汇总报告")
    print("=" * 80)

    print(f"\n{'查询':<30} {'全文搜索平均(ms)':<20} {'混合搜索平均(ms)':<20} {'性能差异':<15}")
    print("-" * 80)

    for query, stats in stats_summary.items():
        ft_avg = stats["full_text"]["avg"] * 1000
        hybrid_avg = stats["hybrid"]["avg"] * 1000
        diff = ((hybrid_avg - ft_avg) / ft_avg * 100) if ft_avg > 0 else 0

        diff_str = f"{diff:+.1f}%"
        print(f"{query[:28]:<30} {ft_avg:<20.2f} {hybrid_avg:<20.2f} {diff_str:<15}")

    # 总体统计
    if stats_summary:
        overall_ft_avg = sum(s["full_text"]["avg"] for s in stats_summary.values()) / len(stats_summary)
        overall_hybrid_avg = sum(s["hybrid"]["avg"] for s in stats_summary.values()) / len(stats_summary)

        print("\n" + "-" * 80)
        print(f"{'总体平均':<30} {overall_ft_avg*1000:<20.2f} {overall_hybrid_avg*1000:<20.2f}")

        total_ft = sum(stats["full_text"]["total"] for stats in stats_summary.values())
        total_hybrid = sum(stats["hybrid"]["total"] for stats in stats_summary.values())
        print(f"{'总耗时':<30} {total_ft*1000:<20.2f} {total_hybrid*1000:<20.2f}")


def main():
    test_queries = [
        "Children's and Young Adult Literature",
        "Self‑Improvement and Personal Development",
        "Nutrition, Health, and Weight Loss",
        "Cooking and Recipes"
    ]

    try:
        client, collection = connect_to_database()
    except Exception as e:
        print(f"无法连接到数据库: {e}")
        return

    all_comparisons = []
    total_ft_time = 0
    total_hybrid_time = 0

    for query in test_queries:
        ft_results, ft_time = full_text_search(collection, query, limit=10)
        total_ft_time += ft_time

        hybrid_results, hybrid_time = hybrid_search(collection, query, n_results=10)
        total_hybrid_time += hybrid_time

        comparison = compare_results(ft_results, hybrid_results)
        all_comparisons.append({
            "query": query,
            "comparison": comparison,
            "ft_time": ft_time,
            "hybrid_time": hybrid_time
        })

        print_query_comparison(query, ft_results, hybrid_results, ft_time, hybrid_time, comparison)

    print(f"\n总查询数: {len(test_queries)}")
    print(f"全文搜索总耗时: {total_ft_time*1000:.2f} ms")
    print(f"混合搜索总耗时: {total_hybrid_time*1000:.2f} ms")
    print(f"全文搜索平均耗时: {(total_ft_time/len(test_queries))*1000:.2f} ms")
    print(f"混合搜索平均耗时: {(total_hybrid_time/len(test_queries))*1000:.2f} ms")

    total_ft_results = sum(c["comparison"]["full_text_count"] for c in all_comparisons)
    total_hybrid_results = sum(c["comparison"]["hybrid_count"] for c in all_comparisons)
    total_common = sum(c["comparison"]["common_count"] for c in all_comparisons)

    print(f"全文搜索总结果数: {total_ft_results}")
    print(f"混合搜索总结果数: {total_hybrid_results}")
    print(f"共同结果总数: {total_common}")
    print(f"平均重叠率: {(total_common / total_ft_results * 100) if total_ft_results > 0 else 0:.1f}%")

    performance_stats = run_performance_test(collection, test_queries[:5], iterations=3)

    print(f"\n{'查询':<30} {'全文搜索平均(ms)':<20} {'混合搜索平均(ms)':<20} {'性能差异':<15}")
    print("-" * 80)

    for query, stats in performance_stats.items():
        ft_avg = stats["full_text"]["avg"] * 1000
        hybrid_avg = stats["hybrid"]["avg"] * 1000
        diff = ((hybrid_avg - ft_avg) / ft_avg * 100) if ft_avg > 0 else 0

        diff_str = f"{diff:+.1f}%"
        print(f"{query[:28]:<30} {ft_avg:<20.2f} {hybrid_avg:<20.2f} {diff_str:<15}")

    overall_ft_avg = sum(s["full_text"]["avg"] for s in performance_stats.values()) / len(performance_stats)
    overall_hybrid_avg = sum(s["hybrid"]["avg"] for s in performance_stats.values()) / len(performance_stats)

    print("\n" + "-" * 80)
    print(f"{'总体平均':<30} {overall_ft_avg*1000:<20.2f} {overall_hybrid_avg*1000:<20.2f}")

    total_ft_time_perf = sum(s["full_text"]["total"] for s in performance_stats.values())
    total_hybrid_time_perf = sum(s["hybrid"]["total"] for s in performance_stats.values())
    print(f"{'总耗时':<30} {total_ft_time_perf*1000:<20.2f} {total_hybrid_time_perf*1000:<20.2f}")


if __name__ == "__main__":
    main()

