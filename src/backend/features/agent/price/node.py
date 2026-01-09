from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.features.agent.price.schema import (
    PriceAnalysis,
    PriceNodeOutput,
    Valuation,
)
from backend.core.config import settings
from backend.features.agent.state import AgentState


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
        print(f"=== Search Report ===\n{search_report}\n====================")

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
5. display_message: ユーザーに表示する日本語メッセージ（例: "一般的な中古相場です。"）

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
        print(f"=== Price Analysis ===\n{analysis}\n======================")

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
            )
        }
    except Exception as e:
        print(f"Price Node LLM Error: {e}")
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
