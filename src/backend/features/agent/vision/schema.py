from typing import Literal, Optional, List
from pydantic import BaseModel, Field

CategoryType = Literal["mass_product", "unique_item", "unknown", "prohibited"]

class InitialAnalysis(BaseModel):
    """画像分析の出力スキーマ"""
    category_type: CategoryType = Field(
        ..., 
        description="画像の分類結果。既製品(mass_product)、一点物/工芸品(unique_item)、不明(unknown)、禁止物(prohibited)から選択"
    )
    item_name: Optional[str] = Field(
        None, 
        description="特定できた場合の商品名。不明な場合はNone"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., 
        description="判定の確信度"
    )
    reasoning: str = Field(
        ..., 
        description="その分類に至った理由。"
    )
    visual_features: List[str] = Field(
        default_factory=list, 
        description="一点物の場合の視覚的特徴（素材、技法、スタイルなど）"
    )
    retry_advice: Optional[str] = Field(
        None, 
        description="unknownの場合の再撮影アドバイス"
    )
