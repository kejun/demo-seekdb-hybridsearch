# SeekDB 混合搜索演示

> 使用 SeekDB（AI 原生搜索数据库）实现图书数据的语义搜索与混合搜索功能演示。

## 功能特性

- **语义搜索** - 基于向量相似度的智能语义搜索
- **混合搜索** - 结合向量搜索和元数据过滤的高级搜索
- **元数据过滤** - 支持评分、类型、年份、价格等多维度过滤
- **自动向量化** - 使用 SeekDB 内置的嵌入函数自动将文本转换为向量
- **索引优化** - 支持 HNSW 向量索引和元数据字段索引

## 项目结构

```
demo-seekdb-hybrid-search/
├── import_data.py           # 数据导入主程序
├── hybrid_search.py         # 混合搜索示例
├── requirements.txt         # Python 依赖
├── bestsellers_with_categories.csv  # 图书数据集
├── data/
│   └── processor.py         # 数据处理器
├── database/
│   ├── db_client.py         # 数据库客户端封装
│   └── index_manager.py     # 索引管理器
├── models/
│   └── book_metadata.py     # 数据模型定义
├── utils/
│   └── text_utils.py        # 文本处理工具
├── scripts/
│   ├── create_metadata_indexes.sql  # 索引创建 SQL
│   ├── search_comparison_test.py    # 搜索对比测试
│   └── test_tokenizer.py            # 分词器测试
└── docs/
    ├── seekdb_features_summary.md   # SeekDB 功能总结
    └── seekdb_hybrid_search_tutorial.md  # 混合搜索教程
```

## 快速开始

### 环境要求

- Python 3.10+
- SeekDB 数据库服务（默认端口: 2881）

### 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 导入数据

```bash
python import_data.py
```

该脚本会执行以下操作：
1. 加载 CSV 数据文件
2. 连接 SeekDB 数据库
3. 创建向量集合（384 维，余弦距离）
4. 批量导入图书数据
5. 创建元数据索引
6. 执行测试查询

### 运行混合搜索

```bash
python hybrid_search.py
```

该脚本演示多种搜索场景：
- 纯语义搜索
- 按评分过滤的混合搜索
- 按类型过滤的混合搜索
- 复杂条件组合搜索

## 📖 使用示例

### 语义搜索

```python
import pyseekdb

client = pyseekdb.Client(
    host="127.0.0.1",
    port=2881,
    tenant="sys",
    database="demo_books",
    user="root"
)

collection = client.get_collection("book_info")

# 执行语义搜索
results = collection.query(
    query_texts=["self improvement motivation success"],
    n_results=5,
    include=["metadatas", "documents", "distances"]
)
```

### 混合搜索

```python
# 定义查询条件
query_params = {
    "where_document": {"$contains": "inspirational"},
    "where": {"user_rating": {"$gte": 4.5}},
    "n_results": 5
}

# 定义向量搜索参数
knn_params = {
    "query_texts": ["inspirational life advice"],
    "where": {"user_rating": {"$gte": 4.5}},
    "n_results": 5
}

# 执行混合搜索
results = collection.hybrid_search(
    query=query_params,
    knn=knn_params,
    rank={"rrf": {}},  # 使用 RRF 排序融合
    n_results=5,
    include=["metadatas", "documents", "distances"]
)
```

### 复杂条件过滤

```python
# 组合多个条件：Fiction 类型、2015年后出版、评分 ≥ 4.0
where_condition = {
    "$and": [
        {"year": {"$gte": 2015}},
        {"user_rating": {"$gte": 4.0}},
        {"genre": "Fiction"}
    ]
}

results = collection.hybrid_search(
    query={"where": where_condition, "n_results": 5},
    knn={"query_texts": ["fiction story novel"], "where": where_condition, "n_results": 5},
    rank={"rrf": {}},
    n_results=5
)
```

## 数据模型

### 图书元数据字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | VARCHAR | 书名 |
| `author` | VARCHAR | 作者 |
| `user_rating` | FLOAT | 用户评分 (0.0-5.0) |
| `reviews` | INT | 评论数量 |
| `price` | FLOAT | 价格 |
| `year` | INT | 出版年份 |
| `genre` | VARCHAR | 书籍类型 |

## 🔧 配置说明

### 数据库连接

默认配置：
- Host: `127.0.0.1`
- Port: `2881`
- Tenant: `sys`
- User: `root`
- Database: `demo_books`
- Collection: `book_info`

### 向量配置

- 维度: 384
- 距离度量: 余弦距离 (cosine)
- 索引类型: HNSW

## SeekDB 核心功能

本项目使用了 SeekDB 的以下核心功能：

### AI 原生能力

- ✅ **自动向量化** - `DefaultEmbeddingFunction` 自动处理文本到向量的转换
- ✅ **语义搜索** - 基于向量相似度的智能搜索
- ✅ **混合搜索** - 结合向量搜索和传统 SQL 查询

### 查询能力

- ✅ **元数据过滤** - 支持 `$gte`, `$lte`, `$and` 等运算符
- ✅ **文档内容过滤** - 支持 `$contains` 文本包含搜索
- ✅ **RRF 排序** - Reciprocal Rank Fusion 智能结果融合

### 索引能力

- ✅ **HNSW 向量索引** - 高效的近似最近邻搜索
- ✅ **元数据索引** - 通过生成列优化元数据查询性能
