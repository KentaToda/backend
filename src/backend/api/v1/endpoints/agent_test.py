from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.features.agent.graph import run_agent

router = APIRouter()


# --- Request/Response Models ---
class AgentTestRequest(BaseModel):
    message: str = Field(..., description="エージェントへのメッセージ", examples=["3と4を足してください"])


class AgentTestResponse(BaseModel):
    response: str = Field(..., description="エージェントからの応答")
    llm_calls: int = Field(..., description="LLM呼び出し回数")
    messages: list = Field(..., description="メッセージ履歴")


# --- Endpoint Implementation ---
@router.post("/agent/test", response_model=AgentTestResponse)
async def test_agent(request: AgentTestRequest):
    """
    LangGraphエージェントの疎通確認用エンドポイント

    計算機ツール（add, multiply, divide）を使用した簡易エージェントをテストします。
    例: {"message": "3と4を足してください"}
    """
    try:
        result = await run_agent(message=request.message)

        return AgentTestResponse(
            response=result["response"],
            llm_calls=result["llm_calls"],
            messages=result["messages"],
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
