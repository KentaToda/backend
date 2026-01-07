from fastapi import APIRouter
from backend.api.v1.endpoints import analyze, agent_test

api_router = APIRouter()

# /analyze エンドポイントを登録
api_router.include_router(analyze.router, tags=["analysis"])

# /agent/test エンドポイントを登録
api_router.include_router(agent_test.router, tags=["agent"])