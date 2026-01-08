from typing import Literal, Optional, List
from pydantic import BaseModel, Field

CategoryType = Literal["processable", "unknown", "prohibited"]


class InitialAnalysis(BaseModel):
    """画像分類の出力スキーマ（Node A: 初期分類）"""

    category_type: CategoryType = Field(
        ...,
        description="画像の分類結果。査定可能(processable)、不明(unknown)、禁止物(prohibited)から選択",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="判定の確信度"
    )
    reasoning: str = Field(..., description="その分類に至った理由")
    retry_advice: Optional[str] = Field(
        None, description="unknownの場合の再撮影アドバイス"
    )
    # processableの場合に抽出される商品情報
    item_name: Optional[str] = Field(
        None, description="推定される商品名（ブランド名+商品名など）"
    )
    visual_features: Optional[List[str]] = Field(
        None, description="視覚的特徴のリスト（色、形状、素材、ロゴなど）"
    )
