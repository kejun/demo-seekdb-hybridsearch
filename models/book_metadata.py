import math
import pandas as pd
from dataclasses import dataclass
from utils.text_utils import sanitize_text, ensure_json_safe


class ValidationError(Exception):
    """自定义验证错误异常"""
    pass


@dataclass
class BookMetadata:
    """
    书籍元数据数据类，用于存储和验证书籍信息。

    该类在初始化时会自动清理和验证所有字段，确保数据的有效性和一致性。
    无效数据会被清理为默认值，超出范围的值会抛出 ValidationError 异常。

    Attributes:
        name (str): 书名，最大长度 500 字符，会自动清理文本
        author (str): 作者名，最大长度 200 字符，会自动清理文本
        user_rating (float): 用户评分，范围 0.0-5.0，无效值会抛出异常
        reviews (int): 评论数量，必须 >= 0，无效值会抛出异常
        price (float): 价格，必须 >= 0.0，无效值会抛出异常
        year (int): 出版年份，范围 1900-2100，无效值会抛出异常
        genre (str): 书籍类型，会自动清理文本

    Raises:
        ValidationError: 当字段值超出允许范围时抛出

    Example:
        >>> book = BookMetadata(
        ...     name="Python编程",
        ...     author="John Doe",
        ...     user_rating=4.5,
        ...     reviews=100,
        ...     price=29.99,
        ...     year=2023,
        ...     genre="Non Fiction"
        ... )
        >>> book_dict = book.to_dict()
    """
    name: str
    author: str
    user_rating: float
    reviews: int
    price: float
    year: int
    genre: str

    def __post_init__(self):
        """在初始化后执行验证和清理"""
        # 清理文本字段
        self.name = self._clean_text_field(self.name, max_length=500)
        self.author = self._clean_text_field(self.author, max_length=200)
        self.genre = self._clean_text_field(self.genre)

        # 清理和验证浮点数字段
        self.user_rating = self._clean_float(self.user_rating)
        if not (0.0 <= self.user_rating <= 5.0):
            raise ValidationError(f"user_rating must be between 0.0 and 5.0, got {self.user_rating}")

        self.price = self._clean_float(self.price)
        if self.price < 0.0:
            raise ValidationError(f"price must be >= 0.0, got {self.price}")

        # 清理和验证整数字段
        self.reviews = self._clean_int(self.reviews)
        if self.reviews < 0:
            raise ValidationError(f"reviews must be >= 0, got {self.reviews}")

        self.year = self._clean_int(self.year)
        if not (1900 <= self.year <= 2100):
            raise ValidationError(f"year must be between 1900 and 2100, got {self.year}")

    @staticmethod
    def _clean_text_field(v, max_length=None):
        """清理文本字段"""
        cleaned = sanitize_text(v)
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        return cleaned

    @staticmethod
    def _clean_float(v):
        """清理浮点数字段"""
        if v is None or pd.isna(v):
            return 0.0
        try:
            fval = float(v)
            if hasattr(fval, 'item'):
                fval = fval.item()
            if not math.isfinite(fval):
                return 0.0
            return float(fval)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _clean_int(v):
        """清理整数字段"""
        if v is None or pd.isna(v):
            return 0
        try:
            ival = int(v)
            if hasattr(ival, 'item'):
                ival = ival.item()
            return int(ival)
        except (ValueError, TypeError):
            return 0

    def to_dict(self):
        return ensure_json_safe({
            "name": self.name,
            "author": self.author,
            "user_rating": float(self.user_rating),
            "reviews": int(self.reviews),
            "price": float(self.price),
            "year": int(self.year),
            "genre": self.genre
        })

