from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.v1.router import api_router
from backend.core.config import settings
from backend.core.logging import get_logger, setup_logging

# ロギング初期化
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"GCP Project: {settings.GCP_PROJECT_ID}")
    yield
    # 終了時
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS設定（設定ファイルから取得）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターをアプリケーションに登録
app.include_router(api_router, prefix=settings.API_V1_STR)

# 静的ファイルのパス設定（frontend/ディレクトリ）
# backend/src/backend/main.py から ../../../frontend へのパス
FRONTEND_DIR = Path(__file__).parent.parent.parent.parent / "frontend"

# 静的ファイルの配信設定（frontendディレクトリが存在する場合のみ）
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")


# ローカルデバッグ用 (python app/main.py で起動する場合)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)