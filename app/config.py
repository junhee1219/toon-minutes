from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Database
    database_url: str = "sqlite+aiosqlite:///./toon_minutes.db"

    # External APIs (NanoBanana는 Gemini 이미지 생성 모델이므로 동일한 API 키 사용)
    gemini_api_key: str = ""

    # Storage
    static_dir: str = "app/static"
    images_dir: str = "app/static/images"

    # S3 (선택)
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    s3_region: str = "ap-northeast-2"

    # Environment
    env: str = "prod"  # dev | prod

    # Telegram (선택, prod에서만 동작)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
