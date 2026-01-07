from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # プロジェクト名
    PROJECT_NAME: str = "Ojoya API"
    API_V1_STR: str = "/api/v1"
    
    # AWS Bedrock 設定 (デフォルト値を設定しておくとローカル実行時に楽です)
    AWS_REGION: str = "ap-northeast-1"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    # 検索ツール (Tavily)
    TAVILY_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()