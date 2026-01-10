from typing import Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.core.firebase import AuthError, get_current_user_id
from backend.core.firestore import firestore_client
from backend.core.logging import get_logger
from backend.features.agent.graph import run_price_agent

logger = get_logger(__name__)

router = APIRouter()


# --- Request/Response Models ---
class AnalyzeRequest(BaseModel):
    """査定リクエスト"""

    image_base64: str = Field(..., description="Base64 encoded image string")
    user_comment: str = Field(default="", description="Optional user comment")
    platform: Literal["web", "ios", "android"] = Field(
        default="web", description="Client platform"
    )


class PriceInfo(BaseModel):
    """価格情報"""

    min_price: int = Field(..., description="Minimum price in JPY")
    max_price: int = Field(..., description="Maximum price in JPY")
    currency: str = Field(default="JPY")
    display_message: str = Field(..., description="Message to display to user")


class ConfidenceInfo(BaseModel):
    """信頼度情報"""

    level: Literal["high", "medium", "low"]
    reasoning: str


class AnalyzeResponse(BaseModel):
    """査定レスポンス"""

    # 査定ID
    appraisal_id: Optional[str] = Field(None, description="Appraisal document ID")

    # 商品情報
    item_name: Optional[str] = Field(None, description="Identified product name")
    identified_product: Optional[str] = Field(
        None, description="Fully identified product with attributes"
    )
    visual_features: list[str] = Field(
        default_factory=list, description="Visual features"
    )

    # 分類
    classification: Literal["mass_product", "unique_item", "unknown", "prohibited"]

    # 価格情報（既製品の場合のみ）
    price: Optional[PriceInfo] = None

    # 信頼度
    confidence: Optional[ConfidenceInfo] = None

    # 価格変動要因（既製品の場合のみ）
    price_factors: Optional[list[str]] = Field(
        None, description="Factors affecting price"
    )

    # メッセージ（一点物や査定不可の場合）
    message: Optional[str] = None
    recommendation: Optional[str] = None
    retry_advice: Optional[str] = None


# --- Endpoint Implementation ---
@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(
    request: AnalyzeRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """
    画像をアップロードしてAI鑑定を実行するエンドポイント

    - 認証済みユーザーの場合: 査定結果をFirestoreに保存
    - 未認証の場合: 査定のみ実行（保存なし）
    """
    user_id: Optional[str] = None

    # 認証処理（オプション）
    if authorization:
        try:
            user_id = await get_current_user_id(authorization)
            # ユーザードキュメントを取得または作成
            await firestore_client.get_or_create_user(user_id, request.platform)
            logger.info(f"Authenticated user: {user_id}")
        except AuthError as e:
            logger.warning(f"Auth failed: {e.code} - {e.message}")
            raise HTTPException(status_code=401, detail=e.message)

    try:
        # エージェント実行（vision → search → price）
        result = await run_price_agent(image_data=request.image_base64)

        analysis_result = result.get("analysis_result")
        search_output = result.get("search_output")
        price_output = result.get("price_output")

        # レスポンス構築
        response = _build_response(analysis_result, search_output, price_output)

        # 認証済みユーザーの場合は保存
        if user_id:
            appraisal_id = await firestore_client.save_appraisal(
                user_id=user_id,
                vision_result=analysis_result.model_dump() if analysis_result else None,
                search_result=search_output.model_dump() if search_output else None,
                price_result=price_output.model_dump() if price_output else None,
                user_comment=request.user_comment or None,
            )
            response.appraisal_id = appraisal_id
            logger.info(f"Saved appraisal: {appraisal_id}")

        return response

    except Exception as e:
        logger.error(f"Analyze endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


def _build_response(
    analysis_result,
    search_output,
    price_output,
) -> AnalyzeResponse:
    """エージェント結果からレスポンスを構築"""

    # Vision結果がない場合
    if not analysis_result:
        return AnalyzeResponse(
            classification="unknown",
            message="画像を分析できませんでした",
            retry_advice="もう一度お試しください",
        )

    # prohibited または unknown の場合
    if analysis_result.category_type == "prohibited":
        return AnalyzeResponse(
            classification="prohibited",
            message="この画像は査定対象外です",
            retry_advice=analysis_result.retry_advice,
            confidence=ConfidenceInfo(
                level=analysis_result.confidence,
                reasoning=analysis_result.reasoning,
            ),
        )

    if analysis_result.category_type == "unknown":
        return AnalyzeResponse(
            classification="unknown",
            message="画像から商品を特定できませんでした",
            retry_advice=analysis_result.retry_advice,
            confidence=ConfidenceInfo(
                level=analysis_result.confidence,
                reasoning=analysis_result.reasoning,
            ),
        )

    # processable の場合
    item_name = analysis_result.item_name
    visual_features = analysis_result.visual_features or []

    # Search結果がない場合（エッジケース）
    if not search_output:
        return AnalyzeResponse(
            classification="unknown",
            item_name=item_name,
            visual_features=visual_features,
            message="商品の分類ができませんでした",
            confidence=ConfidenceInfo(
                level=analysis_result.confidence,
                reasoning=analysis_result.reasoning,
            ),
        )

    search_analysis = search_output.analysis

    # unique_item の場合
    if search_analysis.classification == "unique_item":
        return AnalyzeResponse(
            classification="unique_item",
            item_name=item_name,
            visual_features=visual_features,
            message="一点物のため市場価格の算出が困難です",
            recommendation="専門家による査定をお勧めします",
            confidence=ConfidenceInfo(
                level=search_analysis.confidence,
                reasoning=search_analysis.reasoning,
            ),
        )

    # mass_product の場合
    identified_product = search_analysis.identified_product

    # Price結果がない場合（エッジケース）
    if not price_output:
        return AnalyzeResponse(
            classification="mass_product",
            item_name=item_name,
            identified_product=identified_product,
            visual_features=visual_features,
            message="価格情報を取得できませんでした",
            confidence=ConfidenceInfo(
                level=search_analysis.confidence,
                reasoning=search_analysis.reasoning,
            ),
        )

    # 完全な結果
    valuation = price_output.valuation

    return AnalyzeResponse(
        classification="mass_product",
        item_name=item_name,
        identified_product=identified_product,
        visual_features=visual_features,
        price=PriceInfo(
            min_price=valuation.min_price,
            max_price=valuation.max_price,
            currency=valuation.currency,
            display_message=price_output.display_message,
        ),
        confidence=ConfidenceInfo(
            level=valuation.confidence,
            reasoning=search_analysis.reasoning,
        ),
        price_factors=price_output.price_factors,
    )
