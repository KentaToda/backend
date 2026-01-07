from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # プロジェクト名
    PROJECT_NAME: str = "Ojoya API"
    API_V1_STR: str = "/api/v1"

    # Google Cloud Vertex AI 設定
    GCP_PROJECT_ID: str     # .envで設定必須
    GCP_LOCATION: str       # .envで設定必須

    MODEL_VISION_NODE:str   # .envで設定必須

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()