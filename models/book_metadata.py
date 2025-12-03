import math
import pandas as pd
from dataclasses import dataclass
from utils.text_utils import sanitize_text, ensure_json_safe


class ValidationError(Exception):
    """自定义验证错误异常"""
    pass


@dataclass
class BookMetadata:
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

