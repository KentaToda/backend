from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # プロジェクト名
    PROJECT_NAME: str = "Ojoya API"
    API_V1_STR: str = "/api/v1"

    # 環境設定
    ENVIRONMENT: str = "development"  # development, production
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    # Google Cloud Vertex AI 設定
    GCP_PROJECT_ID: str  # .envで設定必須
    GCP_LOCATION: str  # .envで設定必須

    MODEL_VISION_NODE: str  # .envで設定必須
    MODEL_SEARCH_NODE: str

    # Firebase設定（オプション - ADC使用時は不要）
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    # SerpApi設定
    SERPAPI_API_KEY: str = ""  # .envで設定必須
    SERPAPI_TIMEOUT_SECONDS: int = 30
    SERPAPI_IMAGE_EXPIRATION_MINUTES: int = 5  # SerpApi用一時URL有効期限

    # ガードレール設定
    MODEL_GUARDRAIL: str = "gemini-2.0-flash"  # 軽量モデル
    ENABLE_GUARDRAIL_CHECK: bool = True

    # Cloud Storage設定
    GCS_BUCKET_NAME: str = "ojoya-images-dev"  # 本番: ojoya-images-prod
    GCS_IMAGE_EXPIRATION_MINUTES: int = 60  # 署名付きURLの有効期限

    # CORS設定
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)


settings = Settings()