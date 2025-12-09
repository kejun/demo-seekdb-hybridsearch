# SeekDB Hybrid Search Demo

> A demonstration of semantic search and hybrid search capabilities using SeekDB, an AI-native search database, with book data.

## Features

- **Semantic Search** - Intelligent semantic search based on vector similarity
- **Hybrid Search** - Advanced search combining vector search with metadata filtering
- **Metadata Filtering** - Multi-dimensional filtering by rating, genre, year, price, and more
- **Automatic Vectorization** - Automatic text-to-vector conversion using SeekDB's built-in embedding functions
- **Index Optimization** - Support for HNSW vector indexes and metadata field indexes

## Project Structure

```
demo-seekdb-hybrid-search/
├── import_data.py           # Main data import script
├── hybrid_search.py         # Hybrid search examples
├── requirements.txt         # Python dependencies
├── bestsellers_with_categories.csv  # Book dataset
├── data/
│   └── processor.py         # Data processor
├── database/
│   ├── db_client.py         # Database client wrapper
│   └── index_manager.py     # Index manager
├── models/
│   └── book_metadata.py     # Data model definitions
├── utils/
│   └── text_utils.py        # Text processing utilities
├── scripts/
│   ├── create_metadata_indexes.sql  # Index creation SQL
│   ├── search_comparison_test.py    # Search comparison tests
│   └── test_tokenizer.py            # Tokenizer tests
└── docs/
    ├── seekdb_features_summary.md   # SeekDB features summary
    └── seekdb_hybrid_search_tutorial.md  # Hybrid search tutorial
```

## Quick Start

### Requirements

- Python 3.10+
- SeekDB database service (default port: 2881)

### Installation

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Import Data

```bash
python import_data.py
```

This script performs the following operations:
1. Loads CSV data file
2. Connects to SeekDB database
3. Creates a vector collection (384 dimensions, cosine distance)
4. Batch imports book data
5. Creates metadata indexes
6. Executes test queries

### Run Hybrid Search

```bash
python hybrid_search.py
```

This script demonstrates various search scenarios:
- Pure semantic search
- Hybrid search filtered by rating
- Hybrid search filtered by genre
- Complex conditional search combinations

## 📖 Usage Examples

### Semantic Search

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

# Execute semantic search
results = collection.query(
    query_texts=["self improvement motivation success"],
    n_results=5,
    include=["metadatas", "documents", "distances"]
)
```

### Hybrid Search

```python
# Define query conditions
query_params = {
    "where_document": {"$contains": "inspirational"},
    "where": {"user_rating": {"$gte": 4.5}},
    "n_results": 5
}

# Define vector search parameters
knn_params = {
    "query_texts": ["inspirational life advice"],
    "where": {"user_rating": {"$gte": 4.5}},
    "n_results": 5
}

# Execute hybrid search
results = collection.hybrid_search(
    query=query_params,
    knn=knn_params,
    rank={"rrf": {}},  # Use RRF ranking fusion
    n_results=5,
    include=["metadatas", "documents", "distances"]
)
```

### Complex Conditional Filtering

```python
# Combine multiple conditions: Fiction genre, published after 2015, rating ≥ 4.0
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

## Data Model

### Book Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | VARCHAR | Book title |
| `author` | VARCHAR | Author name |
| `user_rating` | FLOAT | User rating (0.0-5.0) |
| `reviews` | INT | Number of reviews |
| `price` | FLOAT | Price |
| `year` | INT | Publication year |
| `genre` | VARCHAR | Book genre |

## 🔧 Configuration

### Database Connection

Default configuration:
- Host: `127.0.0.1`
- Port: `2881`
- Tenant: `sys`
- User: `root`
- Database: `demo_books`
- Collection: `book_info`

### Vector Configuration

- Dimensions: 384
- Distance metric: Cosine distance
- Index type: HNSW

## SeekDB Core Features

This project utilizes the following core features of SeekDB:

### AI-Native Capabilities

- ✅ **Automatic Vectorization** - `DefaultEmbeddingFunction` automatically handles text-to-vector conversion
- ✅ **Semantic Search** - Intelligent search based on vector similarity
- ✅ **Hybrid Search** - Combines vector search with traditional SQL queries

### Query Capabilities

- ✅ **Metadata Filtering** - Supports operators like `$gte`, `$lte`, `$and`, etc.
- ✅ **Document Content Filtering** - Supports `$contains` text inclusion search
- ✅ **RRF Ranking** - Reciprocal Rank Fusion for intelligent result fusion

### Index Capabilities

- ✅ **HNSW Vector Index** - Efficient approximate nearest neighbor search
- ✅ **Metadata Indexes** - Optimizes metadata query performance through generated columns
