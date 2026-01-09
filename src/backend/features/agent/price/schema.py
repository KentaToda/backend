from pydantic import BaseModel
from typing import Literal, Optional


class Valuation(BaseModel):
    """価格評価情報"""
    min_price: int
    max_price: int
    currency: Literal["JPY"] = "JPY"
    confidence: Literal["high", "medium", "low"]


class UpsidePotential(BaseModel):
    """潜在的な高価値の可能性"""
    has_potential: bool
    trigger_factor: Optional[str] = None  # 何があれば高いか
    potential_max_price: Optional[int] = None
    user_message: Optional[str] = None


class PriceAnalysis(BaseModel):
    """LLM出力用スキーマ (シンプル版)"""
    min_price: int
    max_price: int
    confidence: Literal["high", "medium", "low"]
    reasoning: str
    display_message: str


class PriceNodeOutput(BaseModel):
    """価格検索ノードの最終出力 (シンプル版)"""
    status: Literal["complete", "error"]
    valuation: Valuation
    display_message: str
