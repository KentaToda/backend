"""
Vision Node - SerpApi Google Lens統合

画像をGoogle Lensで検索し、商品情報を取得する。
軽量LLMによるガードレールチェックも実施。
"""

import asyncio
import re
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.serpapi import serpapi_client
from backend.core.storage import storage_client
from backend.features.agent.state import AgentState
from backend.features.agent.vision.schema import InitialAnalysis
from backend.features.agent.vision.serpapi_schema import GoogleLensResponse

logger = get_logger(__name__)


def _extract_image_base64_from_messages(messages: list) -> Optional[str]:
    """メッセージから画像Base64を抽出"""
    for msg in messages:
        if hasattr(msg, "content") and isinstance(msg.content, list):
            for content in msg.content:
                if isinstance(content, dict) and content.get("type") == "image_url":
                    image_url = content.get("image_url", {})
                    url = image_url.get("url", "") if isinstance(image_url, dict) else image_url
                    # data:image/...;base64,... 形式から抽出
                    if url.startswith("data:image"):
                        match = re.match(r"data:image/[^;]+;base64,(.+)", url)
                        if match:
                            return match.group(1)
                        return url.split(",", 1)[-1] if "," in url else None
    return None


def _map_lens_result_to_analysis(
    lens_result: GoogleLensResponse,
) -> InitialAnalysis:
    """Google Lens結果をInitialAnalysisにマッピング"""

    if lens_result.status == "Error":
        return InitialAnalysis(
            category_type="unknown",
            confidence="low",
            reasoning=f"Google Lens検索エラー: {lens_result.error_message}",
            retry_advice="しばらく待ってからもう一度お試しください。",
        )

    if not lens_result.has_matches:
        return InitialAnalysis(
            category_type="unknown",
            confidence="low",
            reasoning="Google Lensで類似商品が見つかりませんでした。",
            retry_advice="別の角度から撮影するか、商品全体が写るようにしてください。",
        )

    # 商品名を取得
    item_name = lens_result.get_item_name()

    # 視覚的特徴を取得
    visual_features = lens_result.get_visual_features(max_items=5)

    # 信頼度を判定
    confidence = "high"
    if len(lens_result.visual_matches) < 3:
        confidence = "medium"
    if not lens_result.knowledge_graph:
        confidence = "medium" if confidence == "high" else "low"

    match_count = len(lens_result.visual_matches)
    reasoning = f"Google Lensで{match_count}件の類似商品を検出しました。"
    if lens_result.knowledge_graph and lens_result.knowledge_graph.title:
        reasoning += f" 商品名: {lens_result.knowledge_graph.title}"

    return InitialAnalysis(
        category_type="processable",
        confidence=confidence,
        reasoning=reasoning,
        item_name=item_name,
        visual_features=visual_features,
    )


async def _check_guardrails(messages: list) -> Optional[InitialAnalysis]:
    """
    軽量LLMでガードレールチェック

    禁止コンテンツ（顔、個人情報など）を検出した場合はInitialAnalysisを返す。
    問題なければNoneを返す。
    """
    if not settings.ENABLE_GUARDRAIL_CHECK:
        return None

    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_GUARDRAIL,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0,
            max_tokens=50,
            vertexai=True,
        )

        guardrail_prompt = """画像に以下が含まれているか確認してください:
- 人物の顔が明確に写っている（モデル着用の商品写真は除く）
- 個人情報（住所、電話番号、クレジットカード番号など）
- 現金、有価証券
- 生きている動植物

上記のいずれかが含まれていれば「prohibited」、そうでなければ「ok」とだけ回答してください。"""

        guardrail_messages = [SystemMessage(content=guardrail_prompt)] + messages

        result = await llm.ainvoke(guardrail_messages)

        if "prohibited" in result.content.lower():
            logger.info("Guardrail detected prohibited content")
            return InitialAnalysis(
                category_type="prohibited",
                confidence="high",
                reasoning="禁止されているコンテンツが検出されました。人物の顔、個人情報、現金などは査定対象外です。",
            )

        return None

    except Exception as e:
        logger.warning(f"Guardrail check failed, continuing: {e}")
        return None


async def _vision_node_async(state: "AgentState") -> dict:
    """Vision Nodeの非同期実装"""

    messages = state["messages"]

    # Step 1: 画像Base64を抽出
    image_base64 = _extract_image_base64_from_messages(messages)
    if not image_base64:
        logger.error("No image found in messages")
        return {
            "analysis_result": InitialAnalysis(
                category_type="unknown",
                confidence="low",
                reasoning="画像が見つかりませんでした。",
                retry_advice="画像を添付してください。",
            )
        }

    # Step 2: ガードレールチェック（並行実行のため先に開始）
    guardrail_task = asyncio.create_task(_check_guardrails(messages))

    # Step 3: SerpApi用に画像をGCSにアップロード
    try:
        image_url = await storage_client.upload_temp_image_for_serpapi(image_base64)
    except Exception as e:
        logger.error(f"Failed to upload image for SerpApi: {e}")
        return {
            "analysis_result": InitialAnalysis(
                category_type="unknown",
                confidence="low",
                reasoning=f"画像のアップロードに失敗しました: {str(e)}",
                retry_advice="もう一度お試しください。",
            )
        }

    # Step 4: SerpApi Google Lens検索
    lens_result = await serpapi_client.search_by_image_url(
        image_url=image_url,
        search_type="products",
    )

    # Step 5: ガードレール結果を確認
    guardrail_result = await guardrail_task
    if guardrail_result:
        return {"analysis_result": guardrail_result}

    # Step 6: Google Lens結果をマッピング
    analysis = _map_lens_result_to_analysis(lens_result)

    logger.info(
        f"Vision node completed: category={analysis.category_type}, "
        f"confidence={analysis.confidence}, item={analysis.item_name}"
    )

    return {"analysis_result": analysis}


def vision_node(state: "AgentState") -> dict:
    """
    Vision Node - SerpApi Google Lens統合

    1. 画像をGCSにアップロード
    2. SerpApi Google Lensで検索
    3. 軽量LLMでガードレールチェック
    4. 結果をInitialAnalysisにマッピング
    """
    try:
        # 非同期処理を実行
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 既存のイベントループがある場合（FastAPI内など）
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _vision_node_async(state))
                return future.result()
        else:
            return asyncio.run(_vision_node_async(state))

    except Exception as e:
        logger.error(f"Vision node error: {e}", exc_info=True)
        return {
            "analysis_result": InitialAnalysis(
                category_type="unknown",
                confidence="low",
                reasoning=f"System Error: {str(e)}",
                retry_advice="システムエラーが発生しました。もう一度お試しください。",
            )
        }
