from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from backend.core.firebase import AuthError, get_current_user_id
from backend.core.firestore import firestore_client
from backend.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/appraisals")
async def get_appraisal_history(
    limit: int = Query(default=20, ge=1, le=100, description="取得件数"),
    offset: int = Query(default=0, ge=0, description="スキップ件数"),
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """
    ユーザーの査定履歴を取得するエンドポイント
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="認証が必要です")

    try:
        user_id = await get_current_user_id(authorization)
    except AuthError as e:
        logger.warning(f"Auth failed: {e.code} - {e.message}")
        raise HTTPException(status_code=401, detail=e.message)

    try:
        appraisals = await firestore_client.get_appraisal_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        return appraisals
    except Exception as e:
        logger.error(f"Failed to get appraisal history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/appraisals/{appraisal_id}")
async def get_appraisal(
    appraisal_id: str,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """
    特定の査定結果を取得するエンドポイント
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="認証が必要です")

    try:
        user_id = await get_current_user_id(authorization)
    except AuthError as e:
        logger.warning(f"Auth failed: {e.code} - {e.message}")
        raise HTTPException(status_code=401, detail=e.message)

    try:
        appraisal = await firestore_client.get_appraisal(
            user_id=user_id,
            appraisal_id=appraisal_id,
        )

        if appraisal is None:
            raise HTTPException(status_code=404, detail="査定が見つかりません")

        return appraisal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get appraisal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/users/me")
async def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """
    現在のユーザー情報を取得するエンドポイント
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="認証が必要です")

    try:
        user_id = await get_current_user_id(authorization)
    except AuthError as e:
        logger.warning(f"Auth failed: {e.code} - {e.message}")
        raise HTTPException(status_code=401, detail=e.message)

    try:
        user = await firestore_client.get_or_create_user(user_id)
        return user
    except Exception as e:
        logger.error(f"Failed to get user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
