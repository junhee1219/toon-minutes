from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Database
    database_url: str = "sqlite+aiosqlite:///./toon_minutes.db"

    # External APIs
    gemini_api_key: str = ""
    nanobanana_api_key: str = ""

    # Storage
    static_dir: str = "app/static"
    images_dir: str = "app/static/images"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
