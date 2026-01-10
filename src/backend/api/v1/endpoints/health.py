"""
ヘルスチェック・接続確認エンドポイント
"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.firestore import firestore_client
from backend.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"


class FirestoreCheckResponse(BaseModel):
    status: str
    project_id: str | None = None
    document_exists: bool | None = None
    error: str | None = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    基本的なヘルスチェック
    """
    return HealthResponse(status="healthy")


@router.get("/health/firestore", response_model=FirestoreCheckResponse)
async def firestore_health_check():
    """
    Firestore接続確認
    """
    logger.info("Checking Firestore connection...")
    result = await firestore_client.check_connection()
    return FirestoreCheckResponse(
        status=result.get("status", "unknown"),
        project_id=settings.GCP_PROJECT_ID,
        document_exists=result.get("document_exists"),
        error=result.get("error"),
    )
