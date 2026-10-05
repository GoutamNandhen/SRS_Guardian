from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./srs_guardian.db"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 10
    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_CACHE_PATH: str = "data/cache/llm_cache.json"
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.80

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
