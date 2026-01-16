"""SerpApi Google Lens クライアント"""

from typing import Optional

import httpx

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.features.agent.vision.serpapi_schema import (
    GoogleLensResponse,
    GoogleLensVisualMatch,
    GoogleLensKnowledgeGraph,
)

logger = get_logger(__name__)

SERPAPI_BASE_URL = "https://serpapi.com/search"


class SerpApiError(Exception):
    """SerpApi関連のエラー"""

    pass


class SerpApiClient:
    """SerpApi Google Lens クライアント"""

    def __init__(self):
        self.api_key = settings.SERPAPI_API_KEY
        self.timeout = settings.SERPAPI_TIMEOUT_SECONDS

    async def search_by_image_url(
        self,
        image_url: str,
        search_type: str = "products",
        language: str = "ja",
        country: str = "jp",
    ) -> GoogleLensResponse:
        """
        Google Lens画像検索を実行

        Args:
            image_url: 検索する画像のURL
            search_type: 検索タイプ ("products", "visual_matches", "all")
            language: 言語コード
            country: 国コード

        Returns:
            GoogleLensResponse: 検索結果
        """
        if not self.api_key:
            logger.error("SERPAPI_API_KEY is not configured")
            return GoogleLensResponse(
                status="Error",
                error_message="SerpApi API key is not configured",
            )

        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": self.api_key,
            "hl": language,
            "country": country,
        }

        logger.info(f"SerpApi Google Lens search: type={search_type}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(SERPAPI_BASE_URL, params=params)

                if response.status_code != 200:
                    logger.error(f"SerpApi HTTP error: {response.status_code}")
                    return GoogleLensResponse(
                        status="Error",
                        error_message=f"HTTP error: {response.status_code}",
                    )

                data = response.json()
                return self._parse_response(data)

        except httpx.TimeoutException:
            logger.error("SerpApi request timed out")
            return GoogleLensResponse(
                status="Error",
                error_message="Request timed out",
            )
        except httpx.RequestError as e:
            logger.error(f"SerpApi request error: {e}")
            return GoogleLensResponse(
                status="Error",
                error_message=f"Request error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"SerpApi unexpected error: {e}", exc_info=True)
            return GoogleLensResponse(
                status="Error",
                error_message=f"Unexpected error: {str(e)}",
            )

    def _parse_response(self, data: dict) -> GoogleLensResponse:
        """SerpApiレスポンスをパース"""

        # エラーチェック
        search_metadata = data.get("search_metadata", {})
        if search_metadata.get("status") == "Error":
            return GoogleLensResponse(
                status="Error",
                error_message=data.get("error", "Unknown API error"),
            )

        # visual_matchesをパース
        visual_matches = []
        for match in data.get("visual_matches", []):
            visual_matches.append(
                GoogleLensVisualMatch(
                    position=match.get("position", 0),
                    title=match.get("title", ""),
                    link=match.get("link"),
                    source=match.get("source"),
                    price=match.get("price", {}).get("value") if isinstance(match.get("price"), dict) else match.get("price"),
                    thumbnail=match.get("thumbnail"),
                    in_stock=match.get("in_stock"),
                )
            )

        # knowledge_graphをパース
        knowledge_graph = None
        kg_data = data.get("knowledge_graph")
        if kg_data:
            knowledge_graph = GoogleLensKnowledgeGraph(
                title=kg_data.get("title"),
                subtitle=kg_data.get("subtitle"),
                description=kg_data.get("description"),
                images=kg_data.get("images", []),
            )

        # related_contentからクエリを抽出
        related_queries = []
        for item in data.get("related_content", []):
            if query := item.get("query"):
                related_queries.append(query)

        logger.info(
            f"SerpApi parsed: {len(visual_matches)} visual_matches, "
            f"knowledge_graph={'yes' if knowledge_graph else 'no'}"
        )

        return GoogleLensResponse(
            status="Success",
            visual_matches=visual_matches,
            knowledge_graph=knowledge_graph,
            related_queries=related_queries,
        )


# シングルトンインスタンス
serpapi_client = SerpApiClient()
