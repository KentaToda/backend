from fastapi import APIRouter
from backend.api.v1.endpoints import analyze

api_router = APIRouter()

# /analyze エンドポイントを登録
api_router.include_router(analyze.router, tags=["analysis"])