from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Feature層のロジックをインポート
from backend.features.agent.graph import run_analyze_agent

router = APIRouter()

# --- Request/Response Models ---
class AnalyzeRequest(BaseModel):
    # 画像はBase64文字列として受け取る想定
    image_base64: str = Field(..., description="Base64 encoded image string")
    # ユーザーからの補足コメント（任意）
    user_comment: str = Field(default="", description="Optional user comment")

class AnalyzeResponse(BaseModel):
    item_name: str
    price_range: str
    advice: str

# --- Endpoint Implementation ---
@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(request: AnalyzeRequest):
    """
    画像をアップロードしてAI鑑定を実行するエンドポイント
    """
    try:
        # ここで認証やチケット消費ロジックを挟む (Future Work)
        # verify_user(...)
        # consume_ticket(...)

        # エージェント機能の呼び出し
        result = await run_analyze_agent(
            image_data=request.image_base64,
            user_query=request.user_comment
        )
        
        return AnalyzeResponse(
            item_name=result["item_name"],
            price_range=result["price_range"],
            advice=result["advice"]
        )

    except Exception as e:
        # エラーハンドリング
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")