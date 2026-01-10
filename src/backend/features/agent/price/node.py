from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.core.config import settings
from backend.core.llm_callbacks import get_llm_callbacks
from backend.core.logging import get_logger
from backend.features.agent.price.schema import (
    PriceAnalysis,
    PriceNodeOutput,
    Valuation,
)
from backend.features.agent.state import AgentState

logger = get_logger(__name__)


def price_node(state: AgentState) -> dict:
    """
    Node Price: 価格検索ノード（2段階処理版）

    責務:
    1. search_nodeから受け取った商品情報で中古市場相場を検索
    2. 価格レンジ（最安〜最高）を算出

    処理フロー:
    - Step 1: Google Search Grounding でレポート作成（テキスト出力）
    - Step 2: レポートから価格情報を抽出（構造化出力）

    注意: このノードはgraph.pyの条件分岐でmass_productの場合のみ呼ばれる
    """

    # search_nodeの結果から商品情報を取得
    search_output = state.get("search_output")
    analysis_result = state.get("analysis_result")

    identified_product = (
        search_output.analysis.identified_product if search_output else None
    )
    visual_features = (
        analysis_result.visual_features if analysis_result else []
    )

    # 検索クエリを構築（シンプルに）
    search_query_parts = []
    if identified_product:
        # カンマを空白に変換（例: "NIKE Free RN Flyknit, 赤" → "NIKE Free RN Flyknit 赤"）
        product_name = identified_product.replace(",", " ")
        search_query_parts.append(product_name)
    search_query_parts.extend(["メルカリ", "価格"])

    search_query = " ".join(search_query_parts)

    # ========================================
    # Step 1: Google Search で相場レポートを作成
    # ========================================
    llm_search = ChatGoogleGenerativeAI(
        model=settings.MODEL_SEARCH_NODE,
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_LOCATION,
        temperature=0,
        max_retries=2,
        vertexai=True,
        callbacks=get_llm_callbacks("price.search"),
    )

    search_prompt = f"""
あなたは熟練の鑑定士AIエージェント『Ojoya』です。
以下の商品について、中古市場での相場価格を調査してください。

【商品情報】
- 商品名: {identified_product or "不明"}
- 視覚的特徴: {", ".join(visual_features) if visual_features else "なし"}

【検索クエリ】
「{search_query}」で検索して、以下を確認してください:
- メルカリ、ヤフオク、楽天フリマ等での中古販売価格
- 販売履歴や出品価格の傾向
- 状態による価格差

【タスク】
Google検索で中古市場の相場を調査し、以下の内容を含むレポートを作成してください:
1. 見つかった価格情報（最安値、最高値、平均的な価格帯）
2. 価格のばらつきと理由（状態、付属品の有無など）
3. 検索で見つかった具体的な情報源（メルカリ、ヤフオクなど）
4. 同シリーズ・類似商品の相場も含めて推定できる場合はその情報
5. 価格に影響を与える要因（年代、カラー、限定版、付属品の有無など）

【価格変動要因について】
ユーザーがフリマ出品や買取査定の参考にするため、以下のような価格変動要因を必ず調査してください:
- 発売年・モデル年による価格差（例: 2020年モデルは○○円、2018年以前は△△円）
- カラーバリエーションによる価格差（例: 限定カラーは+○○円）
- 状態による価格差（例: 新品同様は○○円、使用感ありは△△円）
- 付属品の有無による価格差（例: 箱・保証書ありで+○○円）
- 限定版・コラボモデルの場合はその旨と価格への影響

【注意】
- 同じ商品の完全一致データがなくても、同シリーズ・同モデルの相場から推定してOK
- 色やサイズ違いでも、同じ商品ラインの相場は参考にできる
- 類似商品すら見つからない場合は、その旨を明記すること
"""

    search_messages = [
        SystemMessage(content=search_prompt),
        HumanMessage(content=f"「{search_query}」で中古市場の相場を調べて、レポートを作成してください。"),
    ]

    try:
        # Step 1: 検索してレポート作成（Grounding + テキスト出力）
        search_response = llm_search.invoke(search_messages, tools=[{"google_search": {}}])
        search_report = search_response.content
        logger.debug(f"Search Report: {search_report}")

        # ========================================
        # Step 2: レポートから価格情報を抽出
        # ========================================
        llm_extract = ChatGoogleGenerativeAI(
            model=settings.MODEL_SEARCH_NODE,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0,
            max_retries=2,
            vertexai=True,
            callbacks=get_llm_callbacks("price.extract"),
        )

        structured_llm = llm_extract.with_structured_output(PriceAnalysis)

        extract_prompt = f"""
以下の相場調査レポートから、価格情報を抽出してください。

【レポート】
{search_report}

【抽出項目】
1. min_price: 最低価格（円）※情報がない場合は 0
2. max_price: 最高価格（円）※情報がない場合は 0
3. confidence: "high", "medium", "low" のいずれか
4. reasoning: 価格算出の根拠
5. display_message: ユーザーに表示する日本語メッセージ（例: "メルカリでの一般的な中古相場です"）
6. price_factors: 価格に影響を与える要因のリスト（配列形式）

【price_factors の出力形式】
ユーザーがフリマ出品や買取査定の価格設定に活用できるよう、具体的な情報を出力してください:
- 各要因は「要因: 価格への影響」の形式で記載
- 例: ["2020年以降のモデルは8000-12000円、それ以前は5000-8000円", "箱・付属品ありで+1000-2000円", "限定カラーは通常より20%高め"]
- 価格変動要因が見つからない場合は null

【注意】
- レポート内に価格情報がある場合は、それを min_price, max_price として抽出
- 情報が不十分な場合は confidence: "low"
- 類似商品の相場から推定した場合も有効な価格として扱う
- 価格情報が全く見つからない場合のみ min_price=0, max_price=0 とする
"""

        extract_messages = [
            SystemMessage(content=extract_prompt),
            HumanMessage(content="レポートから価格情報を抽出してください。"),
        ]

        # Step 2: レポートから抽出（構造化出力のみ、Grounding なし）
        analysis = structured_llm.invoke(extract_messages)
        logger.debug(f"Price Analysis: {analysis}")

        # PriceAnalysis を PriceNodeOutput に変換
        valuation = Valuation(
            min_price=analysis.min_price,
            max_price=analysis.max_price,
            currency="JPY",
            confidence=analysis.confidence,
        )

        # ステータス判定
        if analysis.min_price == 0 and analysis.max_price == 0:
            status = "error"
        else:
            status = "complete"

        return {
            "price_output": PriceNodeOutput(
                status=status,
                valuation=valuation,
                display_message=analysis.display_message,
                price_factors=analysis.price_factors,
            )
        }
    except Exception as e:
        logger.error(f"Price Node LLM Error: {e}", exc_info=True)
        # フォールバック: エラー状態を返す
        return {
            "price_output": PriceNodeOutput(
                status="error",
                valuation=Valuation(
                    min_price=0,
                    max_price=0,
                    currency="JPY",
                    confidence="low",
                ),
                display_message=f"価格検索中にエラーが発生しました: {str(e)}",
            )
        }
