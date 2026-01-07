from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # プロジェクト名
    PROJECT_NAME: str = "Ojoya API"
    API_V1_STR: str = "/api/v1"

    # Google Cloud Vertex AI 設定
    GCP_PROJECT_ID: str  # .envで設定必須
    GCP_LOCATION: str = "us-central1"
    VERTEX_AI_MODEL_ID: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()