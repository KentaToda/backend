from langgraph.graph import StateGraph, START, END
from backend.features.agent.state import AgentState
from backend.features.agent.vision.node import vision_node
from backend.features.agent.search.node import search_node
from backend.features.agent.price.node import price_node


# ---------------------------------------------------------
# 条件分岐関数
# ---------------------------------------------------------
def should_search(state: AgentState) -> str:
    """
    vision_nodeの結果に基づいて検索を行うかどうかを判定する。
    processableの場合のみ検索を実行する。
    """
    analysis = state.get("analysis_result")
    if analysis and analysis.category_type == "processable":
        return "search"
    return "end"


def should_price(state: AgentState) -> str:
    """
    search_nodeの結果に基づいて価格検索を行うかどうかを判定する。
    mass_productの場合のみ価格検索を実行する。
    """
    search_output = state.get("search_output")
    if search_output and search_output.analysis.classification == "mass_product":
        return "price"
    return "end"


# ---------------------------------------------------------
# グラフの構築
# ---------------------------------------------------------
workflow = StateGraph(AgentState)

# ノードの追加
workflow.add_node("node_vision", vision_node)
workflow.add_node("node_search", search_node)
workflow.add_node("node_price", price_node)

# エッジの追加
workflow.add_edge(START, "node_vision")

# 条件分岐: processableの場合のみsearch_nodeへ
workflow.add_conditional_edges(
    "node_vision",
    should_search,
    {
        "search": "node_search",
        "end": END,
    },
)

# 条件分岐: mass_productの場合のみprice_nodeへ
workflow.add_conditional_edges(
    "node_search",
    should_price,
    {
        "price": "node_price",
        "end": END,
    },
)
workflow.add_edge("node_price", END)

app = workflow.compile()


# =============================================
# API呼び出し用関数
# =============================================
from langchain_core.messages import HumanMessage

async def run_agent(message: str) -> dict:
    """
    エージェントを実行してレスポンスを返す（テキストのみ）
    
    Args:
        message: ユーザーからのメッセージ
    
    Returns:
        エージェントの応答を含む辞書
    """
    messages = [HumanMessage(content=message)]
    # agent.invoke ではなく app.invoke が正しい
    result = await app.ainvoke({"messages": messages, "retry_count": 0})

    # 最終メッセージを取得 (vision nodeだけの場合は analysis_result を見るべきだが、
    # 汎用的なchat agentとして振る舞うなら messages[-1] を見るのが一般的。
    # 現在の構成では vision_node は messages を追加せず analysis_result を更新するだけなので、
    # result["analysis_result"] を確認する必要があるかもしれないが、
    # run_agent はテキスト用のようなので一旦そのままにするか、あるいは修正が必要。
    # 今回は vision_agent がメインなのでそちらをしっかり実装する。
    
    # app.ainvoke は非同期で実行するため await が必要
    
    return {
        "response": str(result), # デバッグ用に全体を返す
    }

async def run_vision_agent(image_data: str) -> dict:
    """
    画像データを受け取ってエージェントを実行する
    
    Args:
        image_data: Base64エンコードされた画像文字列 (例: "data:image/jpeg;base64,...")
    """
    
    # LangChainのHumanMessageで画像を渡す形式
    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": image_data},
            }
        ]
    )
    
    # グラフ実行
    # 初期状態として messages と retry_count を渡す
    initial_state = {
        "messages": [message],
        "retry_count": 0
    }
    
    result = await app.ainvoke(initial_state)
    
    # 結果の整形
    # vision_node は analysis_result を返すのでそれを取得
    analysis = result.get("analysis_result")
    
    return {
        "analysis_result": analysis,
        # デバッグ用
        "debug_state": str(result)
    }
# 既存のrun_analyze_agent関数（後方互換性のため残すが、中身は新関数に置き換え推奨）
async def run_analyze_agent(image_data: str) -> dict:
    return await run_vision_agent(image_data)

async def run_search_agent(image_data: str) -> dict:
    """
    画像データを受け取ってvision_node + search_nodeを実行する

    Args:
        image_data: Base64エンコードされた画像文字列 (例: "data:image/jpeg;base64,...")

    Returns:
        analysis_result: vision_nodeの分析結果
        search_output: search_nodeの検索・分類結果（processableの場合のみ）
    """

    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": image_data},
            }
        ]
    )

    initial_state = {
        "messages": [message],
        "retry_count": 0,
    }

    result = await app.ainvoke(initial_state)

    return {
        "analysis_result": result.get("analysis_result"),
        "search_output": result.get("search_output"),
        "debug_state": str(result),
    }


async def run_price_agent(image_data: str) -> dict:
    """
    画像データを受け取ってvision_node + search_node + price_nodeを実行する

    Args:
        image_data: Base64エンコードされた画像文字列 (例: "data:image/jpeg;base64,...")

    Returns:
        analysis_result: vision_nodeの分析結果
        search_output: search_nodeの検索・分類結果（processableの場合のみ）
        price_output: price_nodeの価格検索結果（mass_productの場合のみ）
    """

    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": image_data},
            }
        ]
    )

    initial_state = {
        "messages": [message],
        "retry_count": 0,
    }

    result = await app.ainvoke(initial_state)

    return {
        "analysis_result": result.get("analysis_result"),
        "search_output": result.get("search_output"),
        "price_output": result.get("price_output"),
        "debug_state": str(result),
    }


from typing import AsyncGenerator, Any
import asyncio


async def stream_price_agent(image_data: str) -> AsyncGenerator[dict[str, Any], None]:
    """
    画像データを受け取ってvision_node + search_node + price_nodeをストリーミング実行する

    LangGraphの astream_events を使用してノードの開始・終了イベントをリアルタイムで配信します。

    Args:
        image_data: Base64エンコードされた画像文字列 (例: "data:image/jpeg;base64,...")

    Yields:
        event: LangGraphのイベントオブジェクト
            - event: イベント種別 ("on_chain_start", "on_chain_end" など)
            - name: ノード名 ("node_vision", "node_search", "node_price")
            - data: イベントデータ（ノード終了時は output を含む）
    """
    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": image_data},
            }
        ]
    )

    initial_state = {
        "messages": [message],
        "retry_count": 0,
    }

    # astream_events でノードの開始・終了イベントを取得
    async for event in app.astream_events(initial_state, version="v2"):
        yield event


async def stream_price_agent_with_thinking(
    image_data: str,
    thinking_queue: asyncio.Queue,
) -> dict:
    """
    画像データを受け取ってvision_node + search_node + price_nodeを実行し、
    各ノードの思考過程をキューに送信する

    2段階方式:
    1. 各ノードの処理前に思考過程をストリーミング出力
    2. 構造化出力で結果を抽出

    Args:
        image_data: Base64エンコードされた画像文字列
        thinking_queue: 思考過程を送信するキュー

    Returns:
        analysis_result, search_output, price_output を含む辞書
    """
    from langchain_core.messages import SystemMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    from backend.core.config import settings
    from backend.core.llm_callbacks import StreamingCallbackHandler
    from backend.features.agent.vision.schema import InitialAnalysis
    from backend.features.agent.search.schema import SearchAnalysis, SearchNodeOutput
    from backend.features.agent.price.schema import PriceAnalysis, PriceNodeOutput, Valuation
    from backend.core.logging import get_logger

    logger = get_logger(__name__)

    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": image_data},
            }
        ]
    )

    result = {
        "analysis_result": None,
        "search_output": None,
        "price_output": None,
    }

    # ========================================
    # Vision Node (2段階: 思考ストリーム → 構造化出力)
    # ========================================
    await thinking_queue.put({
        "type": "node_start",
        "node": "vision",
        "message": "画像を解析しています...",
    })

    vision_thinking_prompt = """
あなたは熟練の鑑定士AIエージェント『Ojoya』の「目」です。
ユーザーから送られた画像を分析してください。

【タスク】
画像を見て、あなたの分析過程を日本語で説明してください。
以下の観点で考えを述べてください:

1. 画像に何が写っているか
2. ブランドやメーカーの特定（ロゴ、刻印、デザインの特徴から）
3. 商品名やモデル名の推定
4. 色、素材、状態の観察
5. 査定可能かどうかの判断

考えを述べながら分析を進めてください。
"""

    try:
        # Step 1: 思考過程をストリーミング
        streaming_handler = StreamingCallbackHandler(thinking_queue, "vision")
        thinking_llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_VISION_NODE,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0.3,
            max_retries=2,
            vertexai=True,
            streaming=True,
            callbacks=[streaming_handler],
        )

        thinking_messages = [
            SystemMessage(content=vision_thinking_prompt),
            message,
        ]

        # 思考過程を出力（ストリーミング）
        await thinking_llm.ainvoke(thinking_messages)

        # Step 2: 構造化出力で結果を抽出
        structured_llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_VISION_NODE,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0,
            max_retries=2,
            vertexai=True,
        ).with_structured_output(InitialAnalysis)

        vision_system_prompt = """
あなたは熟練の鑑定士AIエージェント『Ojoya』の「目」です。
ユーザーから送られた画像を分析し、以下のルールに従って厳密に分類してください。

【分類ルール】
1. prohibited (禁止物): 人物の顔が明確、個人情報、現金、生きている動植物
2. unknown (不明): 暗い、ピンボケ、見切れ、判別不能
3. processable (査定可能): 上記以外の有効な商品画像

【processableの場合】
- item_name: ブランド名 + 商品名/シリーズ名（型番があれば含める）
- visual_features: 色、素材、状態、付属品などをリストで

【confidence】
- high: ブランド・商品名が明確に特定できる
- medium: カテゴリは分かるが詳細不明確
- low: 大まかな分類のみ可能
"""

        structured_messages = [
            SystemMessage(content=vision_system_prompt),
            message,
        ]

        analysis_result = await structured_llm.ainvoke(structured_messages)
        result["analysis_result"] = analysis_result

        await thinking_queue.put({
            "type": "node_complete",
            "node": "vision",
            "data": {
                "category_type": analysis_result.category_type,
                "item_name": analysis_result.item_name,
            },
        })

    except Exception as e:
        logger.error(f"Vision Node Error: {e}", exc_info=True)
        result["analysis_result"] = InitialAnalysis(
            category_type="unknown",
            confidence="low",
            reasoning=f"System Error: {str(e)}",
            retry_advice="システムエラーが発生しました。もう一度お試しください。"
        )
        await thinking_queue.put({
            "type": "error",
            "node": "vision",
            "message": str(e),
        })
        return result

    # processable でなければ終了
    if analysis_result.category_type != "processable":
        return result

    # ========================================
    # Search Node (2段階: 思考ストリーム → 構造化出力)
    # ========================================
    await thinking_queue.put({
        "type": "node_start",
        "node": "search",
        "message": "商品名で市場を検索しています...",
    })

    item_name = analysis_result.item_name or "商品"
    visual_features = analysis_result.visual_features or []

    search_thinking_prompt = f"""
あなたは熟練の鑑定士AIエージェント『Ojoya』です。
以下の商品情報を基に、Google検索で市場情報を調べてください。

【商品情報】
- 商品名: {item_name}
- 視覚的特徴: {", ".join(visual_features) if visual_features else "なし"}

【タスク】
この商品について、市場での流通状況を調べて分析過程を説明してください:

1. 検索で見つかった情報
2. ECサイトや中古市場での販売状況
3. メルカリ、ヤフオク等での取引実績
4. 既製品（量産品）か一点物かの判断理由
5. 正式な商品名や型番の特定

考えを述べながら分析を進めてください。
"""

    try:
        # Step 1: 思考過程をストリーミング
        streaming_handler = StreamingCallbackHandler(thinking_queue, "search")
        thinking_llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_SEARCH_NODE,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0.3,
            max_retries=2,
            vertexai=True,
            streaming=True,
            callbacks=[streaming_handler],
        )

        thinking_messages = [
            SystemMessage(content=search_thinking_prompt),
            HumanMessage(content=f"「{item_name}」について市場調査してください。"),
        ]

        # Grounding + ストリーミング
        await thinking_llm.ainvoke(thinking_messages, tools=[{"google_search": {}}])

        # Step 2: 構造化出力で結果を抽出
        structured_llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_SEARCH_NODE,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0,
            max_retries=2,
            vertexai=True,
        ).with_structured_output(SearchAnalysis)

        search_system_prompt = f"""
先ほどの調査結果を基に、以下を判定してください。

【分類】
1. mass_product (既製品): 市場で流通している量産品
2. unique_item (一点物): 手作り品、アート作品、相場算出困難

【出力項目】
- classification: "mass_product" または "unique_item"
- confidence: "high", "medium", "low"
- reasoning: 判定理由
- identified_product: 既製品の場合、正式な商品名（一点物はnull）
"""

        search_messages = [
            SystemMessage(content=search_system_prompt),
            HumanMessage(content="調査結果を基に分類してください。"),
        ]

        search_analysis = await structured_llm.ainvoke(search_messages)

        result["search_output"] = SearchNodeOutput(
            search_results=[],
            analysis=search_analysis,
            search_performed=True,
        )

        await thinking_queue.put({
            "type": "node_complete",
            "node": "search",
            "data": {
                "classification": search_analysis.classification,
                "identified_product": search_analysis.identified_product,
            },
        })

    except Exception as e:
        logger.error(f"Search Node Error: {e}", exc_info=True)
        result["search_output"] = SearchNodeOutput(
            search_results=[],
            analysis=SearchAnalysis(
                classification="unique_item",
                confidence="low",
                reasoning=f"検索エラー: {str(e)}",
            ),
            search_performed=False,
        )
        await thinking_queue.put({
            "type": "error",
            "node": "search",
            "message": str(e),
        })
        return result

    # unique_item なら終了
    if search_analysis.classification != "mass_product":
        return result

    # ========================================
    # Price Node (2段階: 思考ストリーム → 構造化出力)
    # ========================================
    await thinking_queue.put({
        "type": "node_start",
        "node": "price",
        "message": "価格帯を分析しています...",
    })

    identified_product = search_analysis.identified_product or item_name

    price_thinking_prompt = f"""
あなたは熟練の鑑定士AIエージェント『Ojoya』です。
以下の商品について、中古市場での相場価格を調査してください。

【商品情報】
- 商品名: {identified_product}
- 視覚的特徴: {", ".join(visual_features) if visual_features else "なし"}

【タスク】
この商品の中古相場を調べて、分析過程を説明してください:

1. メルカリ、ヤフオク等での販売価格
2. 状態による価格差
3. 最安値と最高値の範囲
4. 価格に影響を与える要因（年代、カラー、付属品など）

具体的な価格情報を含めて説明してください。
"""

    try:
        # Step 1: 思考過程をストリーミング
        streaming_handler = StreamingCallbackHandler(thinking_queue, "price")
        thinking_llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_SEARCH_NODE,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0.3,
            max_retries=2,
            vertexai=True,
            streaming=True,
            callbacks=[streaming_handler],
        )

        thinking_messages = [
            SystemMessage(content=price_thinking_prompt),
            HumanMessage(content=f"「{identified_product} メルカリ 価格」で中古相場を調べてください。"),
        ]

        # Grounding + ストリーミング
        await thinking_llm.ainvoke(thinking_messages, tools=[{"google_search": {}}])

        # Step 2: 構造化出力で結果を抽出
        structured_llm = ChatGoogleGenerativeAI(
            model=settings.MODEL_SEARCH_NODE,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            temperature=0,
            max_retries=2,
            vertexai=True,
        ).with_structured_output(PriceAnalysis)

        price_system_prompt = """
先ほどの調査結果から価格情報を抽出してください。

【出力項目】
- min_price: 最低価格（円）
- max_price: 最高価格（円）
- confidence: "high", "medium", "low"
- reasoning: 価格算出の根拠
- display_message: ユーザー向けメッセージ
- price_factors: 価格変動要因のリスト（例: "箱ありで+1000円"）
"""

        price_messages = [
            SystemMessage(content=price_system_prompt),
            HumanMessage(content="調査結果から価格情報を抽出してください。"),
        ]

        price_analysis = await structured_llm.ainvoke(price_messages)

        valuation = Valuation(
            min_price=price_analysis.min_price,
            max_price=price_analysis.max_price,
            currency="JPY",
            confidence=price_analysis.confidence,
        )

        status = "complete" if price_analysis.min_price > 0 else "error"

        result["price_output"] = PriceNodeOutput(
            status=status,
            valuation=valuation,
            display_message=price_analysis.display_message,
            price_factors=price_analysis.price_factors,
        )

        await thinking_queue.put({
            "type": "node_complete",
            "node": "price",
            "data": {
                "min_price": price_analysis.min_price,
                "max_price": price_analysis.max_price,
            },
        })

    except Exception as e:
        logger.error(f"Price Node Error: {e}", exc_info=True)
        result["price_output"] = PriceNodeOutput(
            status="error",
            valuation=Valuation(
                min_price=0,
                max_price=0,
                currency="JPY",
                confidence="low",
            ),
            display_message=f"価格検索エラー: {str(e)}",
        )
        await thinking_queue.put({
            "type": "error",
            "node": "price",
            "message": str(e),
        })

    return result