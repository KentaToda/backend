from fastapi import APIRouter

from backend.api.v1.endpoints import agent_test, analyze, appraisals, health

api_router = APIRouter()

# /health エンドポイントを登録
api_router.include_router(health.router, tags=["health"])

# /analyze エンドポイントを登録
api_router.include_router(analyze.router, tags=["analysis"])

# /appraisals, /users エンドポイントを登録
api_router.include_router(appraisals.router, tags=["appraisals"])

# /agent/test エンドポイントを登録
api_router.include_router(agent_test.router, tags=["agent"])