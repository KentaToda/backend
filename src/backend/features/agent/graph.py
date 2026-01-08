from langgraph.graph import StateGraph, START, END
from backend.features.agent.state import AgentState
from backend.features.agent.vision.node import vision_node
from backend.features.agent.search.node import search_node


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


# ---------------------------------------------------------
# グラフの構築
# ---------------------------------------------------------
workflow = StateGraph(AgentState)

# ノードの追加
workflow.add_node("node_vision", vision_node)
workflow.add_node("node_search", search_node)

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
workflow.add_edge("node_search", END)

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