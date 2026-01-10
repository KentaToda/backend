from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.core.config import settings
from backend.core.llm_callbacks import get_llm_callbacks
from backend.core.logging import get_logger
from backend.features.agent.search.schema import (
    SearchAnalysis,
    SearchNodeOutput,
)
from backend.features.agent.state import AgentState

logger = get_logger(__name__)


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
        callbacks=get_llm_callbacks("search"),
    )

    # 構造化出力を設定
    structured_llm = llm.with_structured_output(SearchAnalysis)

    system_prompt = f"""
あなたは熟練の鑑定士AIエージェント『Ojoya』です。
以下の商品情報を基に、Google検索で最新の市場情報を調べて、「既製品」か「一点物」かを判定してください。

【このエージェントの目的】
ユーザーがフリマアプリへの出品、買取店への持ち込み、または中古品購入の価格検討に活用できる
「中古相場情報」を提供することです。既製品の場合は次のノードで価格検索を行います。

【商品情報（vision_nodeより）】
- 商品名: {item_name or "不明"}
- 視覚的特徴: {", ".join(visual_features) if visual_features else "なし"}

【検索クエリ】
「{search_query}」で検索して、以下を確認してください:
- この商品が市場で流通しているか
- ECサイトや中古市場で同じ商品が販売されているか
- 型番や正式名称が特定できるか
- メルカリ、ヤフオク、楽天フリマなどで取引実績があるか

【分類基準】
1. mass_product (既製品):
   - ブランド品、型番商品、量産品
   - 市場で同じ商品が流通している（新品・中古問わず）
   - ECサイト、フリマアプリ等で購入可能または取引実績がある
   - ※ヴィンテージ品や廃盤品でも、中古市場で流通していれば mass_product

2. unique_item (一点物):
   - 手作り品、アート作品、骨董品（作家物など）
   - 市場に同じものが存在せず、相場が算出できない
   - オーダーメイド品、職人による一品物
   - ※単に「珍しい」「レア」だけでは一点物にしない。市場流通があれば mass_product

【出力項目】
1. classification: "mass_product" または "unique_item"
2. confidence: "high", "medium", "low" のいずれか
3. reasoning: 判定に至った理由（検索で見つかった具体的な情報を含める）
4. identified_product: 既製品の場合、次の価格検索で使用する商品名を出力
   - vision_nodeで推定された商品名「{item_name or "不明"}」を検索で確認・補完する
   - 正式な商品名、型番、カラー名などを特定できれば含める
   - カンマ区切りで属性を追加。括弧は使用しない
   - 例: "NIKE Air Max 90, 白", "Louis Vuitton ネヴァーフル MM, ダミエ・エベヌ"
   - 一点物の場合は null

【confidenceの判断基準】
- high: 検索で同一商品の取引実績や商品ページが複数見つかった
- medium: 同シリーズや類似商品は見つかるが、完全一致は見つからない
- low: 関連情報が少なく、分類の確信度が低い

【注意事項】
- 迷った場合は mass_product 寄りで判断してください（価格検索で相場が見つからなければユーザーに伝えられるため）
- Google検索で見つかった具体的な情報（サイト名、価格帯など）を reasoning に含めてください
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
        logger.error(f"Search Node LLM Error: {e}", exc_info=True)
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
