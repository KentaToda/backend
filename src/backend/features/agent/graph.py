# LangGraph エージェント実装
# 公式ドキュメント参考: https://docs.langchain.com/oss/python/langgraph/quickstart

import operator
from typing import Literal, Annotated

from langchain_core.tools import tool
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI 
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from backend.core.config import settings


# =============================================
# Step 1: ツールの定義
# =============================================
@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b


# ツールのリストと辞書
tools = [add, multiply, divide]
tools_by_name = {t.name: t for t in tools}


# =============================================
# Step 2: モデルの初期化（遅延初期化）
# =============================================
def get_model_with_tools():
    """Google Vertex AIを使用したモデルを取得"""
    model = ChatGoogleGenerativeAI (
        model=settings.VERTEX_AI_MODEL_ID,
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_LOCATION,
        temperature=0
    )
    return model.bind_tools(tools)


# =============================================
# Step 3: 状態の定義
# =============================================
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


# =============================================
# Step 4: ノードの定義
# =============================================
def llm_call(state: MessagesState) -> dict:
    """LLMがツールを呼び出すか判断するノード"""
    model_with_tools = get_model_with_tools()
    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def tool_node(state: MessagesState) -> dict:
    """ツールを実行するノード"""
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        t = tools_by_name[tool_call["name"]]
        observation = t.invoke(tool_call["args"])
        result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
    return {"messages": result}


# =============================================
# Step 5: 条件分岐ロジック
# =============================================
def should_continue(state: MessagesState) -> Literal["tool_node", "__end__"]:
    """ツールを呼び出すか終了するかを判断"""
    messages = state["messages"]
    last_message = messages[-1]
    # LLMがツールを呼び出した場合はtool_nodeへ
    if last_message.tool_calls:
        return "tool_node"
    # そうでなければ終了
    return END


# =============================================
# Step 6: グラフの構築とコンパイル
# =============================================
def build_agent():
    """エージェントグラフを構築"""
    agent_builder = StateGraph(MessagesState)

    # ノードを追加
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)

    # エッジを追加
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        ["tool_node", END],
    )
    agent_builder.add_edge("tool_node", "llm_call")

    return agent_builder.compile()


# エージェントのインスタンス（グローバル）
agent = build_agent()


# =============================================
# API呼び出し用関数
# =============================================
async def run_agent(message: str) -> dict:
    """
    エージェントを実行してレスポンスを返す

    Args:
        message: ユーザーからのメッセージ

    Returns:
        エージェントの応答を含む辞書
    """
    messages = [HumanMessage(content=message)]
    result = agent.invoke({"messages": messages, "llm_calls": 0})

    # 最終メッセージを取得
    final_message = result["messages"][-1]
    
    return {
        "response": final_message.content,
        "llm_calls": result["llm_calls"],
        "messages": [
            {
                "role": getattr(m, "type", "unknown"),
                "content": str(m.content) if hasattr(m, "content") else str(m),
            }
            for m in result["messages"]
        ],
    }


# 既存のrun_analyze_agent関数（後方互換性のため残す）
async def run_analyze_agent(image_data: str, user_query: str = "") -> dict:
    """
    エージェント実行のメイン関数（仮実装）
    API層からはこの関数を呼び出すだけにします。
    """
    print(f"Agent received image data (len): {len(image_data)}")

    # モックの返却値
    return {
        "item_name": "テスト用アイテム (Mock)",
        "price_range": "¥1,000 - ¥2,000",
        "advice": "これはモックの回答です。LangGraphの実装後に正式な回答になります。",
        "raw_response": "AIの思考プロセスがここに入ります",
    }