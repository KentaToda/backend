from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.features.agent.graph import run_agent, run_vision_agent, run_search_agent

router = APIRouter()


# --- Request/Response Models ---
class AgentTestRequest(BaseModel):
    message: str = Field(..., description="エージェントへのメッセージ", examples=["3と4を足してください"])


class AgentTestResponse(BaseModel):
    response: str = Field(..., description="エージェントからの応答")
    llm_calls: int = Field(..., description="LLM呼び出し回数")
    messages: list = Field(..., description="メッセージ履歴")


class AgentVisionRequest(BaseModel):
    image_data: str | None = Field(None, description="Base64 encoded image data", examples=["data:image/jpeg;base64,..."])
    file_path: str | None = Field(None, description="Server side file path for testing", examples=["test_images/test.jpg"])

# --- Endpoint Implementation ---
@router.post("/agent/test", response_model=AgentTestResponse)
async def test_agent(request: AgentTestRequest):
    """
    LangGraphエージェントの疎通確認用エンドポイント
    """
    try:
        result = await run_agent(message=request.message)

        return AgentTestResponse(
            response=result.get("response", ""),
            llm_calls=0, # 仮
            messages=[] # 仮
        )

    except Exception as e:
        print(f"Error: {e}")
        # raise HTTPException(status_code=500, detail=str(e)) # デバッグ用に詳細出す
        raise HTTPException(status_code=500, detail=str(e))


import base64
import mimetypes
import os

@router.post("/agent/vision_test")
async def test_vision_agent(request: AgentVisionRequest):
    """
    画像分析エージェントのテスト用エンドポイント
    
    - image_data (Base64) か file_path (サーバー上のパス) のどちらかを指定してください。
    """
    try:
        image_content = request.image_data

        if request.file_path:
            # ファイルパスが指定された場合、ファイルを読み込んでBase64に変換
            if not os.path.exists(request.file_path):
                raise HTTPException(status_code=400, detail=f"File not found: {request.file_path}")
            
            mime_type, _ = mimetypes.guess_type(request.file_path)
            if not mime_type:
                mime_type = "image/jpeg" # Default

            with open(request.file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                image_content = f"data:{mime_type};base64,{encoded_string}"
        
        if not image_content:
             raise HTTPException(status_code=400, detail="Either image_data or file_path must be provided")

        # 画像データを渡してエージェント実行
        result = await run_vision_agent(image_content)
        return result
    except Exception as e:
        print(f"Error executing vision agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/search_test")
async def test_search_agent(request: AgentVisionRequest):
    """
    画像検索エージェントのテスト用エンドポイント

    vision_node → search_node の一連フローをテスト
    - processableの場合: vision分析 + 画像検索 + 分類判定を実行
    - それ以外の場合: vision分析のみ実行（search_outputはNone）
    """
    try:
        image_content = request.image_data

        if request.file_path:
            if not os.path.exists(request.file_path):
                raise HTTPException(
                    status_code=400, detail=f"File not found: {request.file_path}"
                )

            mime_type, _ = mimetypes.guess_type(request.file_path)
            if not mime_type:
                mime_type = "image/jpeg"

            with open(request.file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                image_content = f"data:{mime_type};base64,{encoded_string}"

        if not image_content:
            raise HTTPException(
                status_code=400, detail="Either image_data or file_path must be provided"
            )

        result = await run_search_agent(image_content)
        return result
    except Exception as e:
        print(f"Error executing search agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
