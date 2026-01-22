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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
