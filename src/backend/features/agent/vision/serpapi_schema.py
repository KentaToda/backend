"""SerpApi Google Lens レスポンススキーマ"""

from typing import Optional, List

from pydantic import BaseModel


class GoogleLensVisualMatch(BaseModel):
    """Google Lens visual_matches 要素"""

    position: int
    title: str
    link: Optional[str] = None
    source: Optional[str] = None
    price: Optional[str] = None  # "$299.99" or "¥5,000" 形式
    thumbnail: Optional[str] = None
    in_stock: Optional[bool] = None


class GoogleLensKnowledgeGraph(BaseModel):
    """Google Lens knowledge_graph データ"""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    images: List[str] = []


class GoogleLensResponse(BaseModel):
    """SerpApi Google Lens レスポンス全体"""

    status: str  # "Success" | "Error"
    visual_matches: List[GoogleLensVisualMatch] = []
    knowledge_graph: Optional[GoogleLensKnowledgeGraph] = None
    related_queries: List[str] = []
    error_message: Optional[str] = None

    @property
    def has_matches(self) -> bool:
        """マッチ結果があるかどうか"""
        return len(self.visual_matches) > 0

    @property
    def top_match(self) -> Optional[GoogleLensVisualMatch]:
        """最上位のマッチ結果"""
        return self.visual_matches[0] if self.visual_matches else None

    def get_item_name(self) -> Optional[str]:
        """
        商品名を取得（knowledge_graph優先、なければtop_match）
        """
        if self.knowledge_graph and self.knowledge_graph.title:
            return self.knowledge_graph.title
        if self.top_match:
            return self.top_match.title
        return None

    def get_visual_features(self, max_items: int = 5) -> List[str]:
        """
        視覚的特徴をマッチ結果から抽出

        Args:
            max_items: 取得する最大アイテム数

        Returns:
            特徴のリスト（ソース名、価格情報など）
        """
        features = []

        # knowledge_graphからの情報
        if self.knowledge_graph:
            if self.knowledge_graph.subtitle:
                features.append(self.knowledge_graph.subtitle)

        # visual_matchesからの情報
        sources_seen = set()
        for match in self.visual_matches[:max_items]:
            # ソース（販売元）を追加
            if match.source and match.source not in sources_seen:
                sources_seen.add(match.source)
                features.append(f"販売: {match.source}")

            # 価格情報があれば追加
            if match.price and len(features) < max_items:
                features.append(f"参考価格: {match.price}")
                break  # 価格は1つだけ

        # related_queriesから補足情報
        for query in self.related_queries[:2]:
            if len(features) < max_items:
                features.append(query)

        return features[:max_items]
