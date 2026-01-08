from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.features.agent.search.schema import (
    SearchAnalysis,
    SearchNodeOutput,
)
from backend.core.config import settings
from backend.features.agent.state import AgentState


def search_node(state: AgentState) -> dict:
    """
    Node B: 画像検索・分類ノード（Grounding with Google Search版）

    責務:
    1. vision_nodeから受け取った商品情報を使ってGoogle検索で市場情報を取得
    2. 既製品(mass_product)か一点物(unique_item)かを判定
    3. 分類結果を返す

    注意: このノードはgraph.pyの条件分岐でprocessableの場合のみ呼ばれる
    """

    # vision_nodeの結果から商品情報を取得
    analysis_result = state.get("analysis_result")
    item_name = analysis_result.item_name if analysis_result else None
    visual_features = analysis_result.visual_features if analysis_result else []

    # 検索クエリを構築
    search_query_parts = []
    if item_name:
        search_query_parts.append(item_name)
    if visual_features:
        search_query_parts.extend(visual_features[:3])  # 最初の3つの特徴を使用

    search_query = " ".join(search_query_parts) if search_query_parts else "商品"

    # LLMを初期化
    llm = ChatGoogleGenerativeAI(
        model=settings.MODEL_SEARCH_NODE,
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_LOCATION,
        temperature=0,
        max_retries=2,
        vertexai=True,
    )

    # 構造化出力を設定
    structured_llm = llm.with_structured_output(SearchAnalysis)

    system_prompt = f"""
あなたは熟練の鑑定士AIエージェント『Ojoya』です。
以下の商品情報を基に、Google検索で最新の市場情報を調べて、「既製品」か「一点物」かを判定してください。

【商品情報（vision_nodeより）】
- 商品名: {item_name or "不明"}
- 視覚的特徴: {", ".join(visual_features) if visual_features else "なし"}

【検索クエリ】
「{search_query}」で検索して、以下を確認してください:
- この商品が市場で流通しているか
- ECサイトや中古市場で同じ商品が販売されているか
- 型番や正式名称が特定できるか

【分類基準】
1. mass_product (既製品):
   - ブランド品、型番商品、量産品
   - 市場で同じ商品が流通している
   - ECサイト等で購入可能

2. unique_item (一点物):
   - 手作り品、アート作品、骨董品
   - 市場に同じものが存在しない
   - 職人による一品物

【出力項目】
1. classification: "mass_product" または "unique_item"
2. confidence: "high", "medium", "low" のいずれか
3. reasoning: 判定に至った理由（検索で見つかった情報を含める）
4. identified_product: 既製品の場合、正式な商品名を出力（例: "NIKE Free RN Flyknit 2018 メンズ ランニングシューズ"）
   - vision_nodeで推定された商品名「{item_name or "不明"}」を検索で確認・補完する
   - 型番、サイズ、カラー名なども特定できれば含める
   - 一点物の場合は null

【注意事項】
- 確信度が低い場合は、その旨を明確にすること
- Google検索で見つかった情報を根拠として含めること
"""

    # テキストベースで検索を実行（画像なし）
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"「{search_query}」について市場での流通状況を調べて、既製品か一点物かを判定してください。"),
    ]

    try:
        # Grounding + 構造化出力で1回のAPI呼び出しで完了
        # structured_llm.invoke() は SearchAnalysis オブジェクトを直接返す
        analysis = structured_llm.invoke(messages, tools=[{"google_search": {}}])

        return {
            "search_output": SearchNodeOutput(
                search_results=[],  # Groundingでは個別の検索結果は取得しない
                analysis=analysis,
                search_performed=True,
            )
        }
    except Exception as e:
        print(f"Search Node LLM Error: {e}")
        # フォールバック: デフォルト判定
        return {
            "search_output": SearchNodeOutput(
                search_results=[],
                analysis=SearchAnalysis(
                    classification="unique_item",
                    confidence="low",
                    reasoning=f"検索エラーのため判定できませんでした: {str(e)}",
                ),
                search_performed=False,
            )
        }
