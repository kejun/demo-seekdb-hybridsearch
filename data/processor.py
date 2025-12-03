import json
import pandas as pd
from typing import List, Dict, Tuple
from models.book_metadata import BookMetadata, ValidationError
from utils.text_utils import sanitize_text, ensure_json_safe


class DataProcessor:
    """
    数据处理器类，用于处理和准备数据以便导入到向量数据库集合中。

    主要功能包括：
    - 从 DataFrame 中提取和准备数据
    - 验证和清理数据以确保 JSON 兼容性
    - 批量将数据添加到向量数据库集合
    - 跟踪验证错误数量
    """

    def __init__(self):
        """
        初始化数据处理器。

        初始化验证错误计数器。
        """
        self.validation_errors = 0

    def prepare_data(self, df: pd.DataFrame) -> Tuple[List[str], List[str], List[Dict]]:
        """
        从 DataFrame 中准备数据，生成 ID、文档和元数据列表。

        Args:
            df: 包含书籍信息的 pandas DataFrame，必须包含以下列：
                - Name: 书名
                - Author: 作者
                - User Rating: 用户评分
                - Reviews: 评论数
                - Price: 价格
                - Year: 年份
                - Genre: 类型

        Returns:
            包含三个列表的元组：
            - ids: 字符串 ID 列表（来自 DataFrame 索引）
            - documents: 文档字符串列表（格式：书名 + 作者）
            - metadatas: 元数据字典列表（包含所有书籍信息）

        Note:
            验证错误数量会在处理过程中重置并更新。
        """
        ids = df.index.astype(str).tolist()
        documents = []
        metadatas = []
        self.validation_errors = 0

        for idx, row in df.iterrows():
            name = sanitize_text(row['Name'])
            author = sanitize_text(row['Author'])
            doc = f"{name} {author}".strip()
            documents.append(doc)
            meta = self._process_row_metadata(idx, row)
            metadatas.append(meta)

        return ids, documents, metadatas

    def _process_row_metadata(self, idx: int, row: pd.Series) -> Dict:
        """
        处理单行数据的元数据，将其转换为 BookMetadata 对象并返回字典格式。

        Args:
            idx: 行的索引
            row: pandas Series 对象，包含一行数据

        Returns:
            包含书籍元数据的字典，如果验证失败则返回默认值

        Note:
            如果数据验证失败，会增加验证错误计数并返回安全的默认值。
        """
        try:
            row_data = {
                'name': row['Name'],
                'author': row['Author'],
                'user_rating': row['User Rating'],
                'reviews': row['Reviews'],
                'price': row['Price'],
                'year': row['Year'],
                'genre': row['Genre']
            }
            book_meta = BookMetadata(**row_data)
            return book_meta.to_dict()
        except ValidationError:
            self.validation_errors += 1
            return ensure_json_safe({
                "name": sanitize_text(row['Name']) or "Unknown",
                "author": sanitize_text(row['Author']) or "Unknown",
                "user_rating": 0.0,
                "reviews": 0,
                "price": 0.0,
                "year": 2000,
                "genre": sanitize_text(row['Genre']) or "Unknown"
            })

    def validate_batch(self, batch_ids: List[str], batch_documents: List[str],
                      batch_metadatas: List[Dict]) -> Tuple[List[str], List[str], List[Dict]]:
        """
        验证一批数据，确保所有数据都是有效的 JSON 格式。

        Args:
            batch_ids: 批次 ID 列表
            batch_documents: 批次文档字符串列表
            batch_metadatas: 批次元数据字典列表

        Returns:
            包含三个列表的元组，只包含通过验证的数据：
            - valid_ids: 有效的 ID 列表
            - valid_documents: 有效的文档列表（已清理为 JSON 安全格式）
            - valid_metadatas: 有效的元数据列表（已清理为 JSON 安全格式）

        Note:
            无法序列化为 JSON 的数据将被跳过，不会包含在返回结果中。
        """
        valid_ids = []
        valid_documents = []
        valid_metadatas = []

        for i in range(len(batch_ids)):
            doc = ensure_json_safe(batch_documents[i])
            meta = ensure_json_safe(batch_metadatas[i])

            try:
                json.dumps(doc, ensure_ascii=False)
                json.dumps(meta, ensure_ascii=False)
                valid_ids.append(batch_ids[i])
                valid_documents.append(doc)
                valid_metadatas.append(meta)
            except Exception:
                continue

        return valid_ids, valid_documents, valid_metadatas

    def add_data_to_collection(self, collection, ids: List[str],
                               documents: List[str], metadatas: List[Dict],
                               batch_size: int = 100, progress_callback=None):
        """
        将数据批量添加到向量数据库集合中。

        Args:
            collection: 向量数据库集合对象，必须实现 add() 方法
            ids: 要添加的 ID 列表
            documents: 要添加的文档字符串列表
            metadatas: 要添加的元数据字典列表
            batch_size: 每批处理的数据量，默认为 100
            progress_callback: 可选的进度回调函数，接收两个参数：
                - current_batch: 当前批次编号（从 1 开始）
                - total_batches: 总批次数

        Note:
            - 数据会被分批处理，每批数据在添加前会进行验证
            - 如果批量添加失败，会自动回退到逐个添加模式
            - 无效的数据会被跳过，不会影响其他数据的添加
            - 空的批次会被自动跳过
        """
        total_batches = (len(ids) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(ids))

            batch_ids = ids[start_idx:end_idx]
            batch_documents = documents[start_idx:end_idx]
            batch_metadatas = metadatas[start_idx:end_idx]

            valid_ids, valid_documents, valid_metadatas = self.validate_batch(
                batch_ids, batch_documents, batch_metadatas
            )

            if len(valid_ids) == 0:
                continue

            try:
                collection.add(
                    ids=valid_ids,
                    documents=valid_documents,
                    metadatas=valid_metadatas
                )
            except Exception:
                self._add_records_individually(
                    collection, valid_ids, valid_documents, valid_metadatas, start_idx
                )

            if progress_callback:
                progress_callback(batch_idx + 1, total_batches)

    def _add_records_individually(self, collection, valid_ids: List[str],
                                  valid_documents: List[str], valid_metadatas: List[Dict],
                                  start_idx: int):
        """
        当批量添加失败时，逐个添加记录到集合中。

        Args:
            collection: 向量数据库集合对象
            valid_ids: 有效的 ID 列表
            valid_documents: 有效的文档列表
            valid_metadatas: 有效的元数据列表
            start_idx: 起始索引（用于错误追踪）

        Note:
            这是一个容错方法，当批量添加失败时自动调用。
            单个记录添加失败会被静默忽略，不会影响其他记录的添加。
        """
        for i in range(len(valid_ids)):
            try:
                collection.add(
                    ids=[valid_ids[i]],
                    documents=[valid_documents[i]],
                    metadatas=[valid_metadatas[i]]
                )
            except Exception:
                pass

