from typing import Literal, Optional, List
from pydantic import BaseModel, Field

# 分類タイプ
ItemClassification = Literal["mass_product", "unique_item"]


class SearchResult(BaseModel):
    """個別の画像検索結果"""

    product_name: Optional[str] = Field(
        None, description="商品名（検索で見つかった場合）"
    )
    brand: Optional[str] = Field(None, description="ブランド名（検索で見つかった場合）")
    similarity_score: float = Field(
        ..., description="類似度スコア (0.0-1.0)", ge=0.0, le=1.0
    )
    source_url: Optional[str] = Field(None, description="検索結果のソースURL")
    is_exact_match: bool = Field(default=False, description="完全一致かどうか")


class SearchAnalysis(BaseModel):
    """LLMによる分類分析結果"""

    classification: ItemClassification = Field(
        ..., description="分類結果: mass_product(既製品) または unique_item(一点物)"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="分類の確信度"
    )
    reasoning: str = Field(..., description="分類に至った理由の説明")
    identified_product: Optional[str] = Field(
        None, description="特定できた場合の商品名（既製品の場合）"
    )


class SearchNodeOutput(BaseModel):
    """search_nodeの出力"""

    search_results: List[SearchResult] = Field(
        default_factory=list, description="画像検索の結果リスト"
    )
    analysis: SearchAnalysis = Field(..., description="LLMによる分類分析結果")
    search_performed: bool = Field(default=True, description="検索が実行されたかどうか")
