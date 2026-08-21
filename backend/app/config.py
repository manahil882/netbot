from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or backend/.env."""

    SUPABASE_URL: str
    SUPABASE_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_NAME: str = "chatbot_docs"
    QDRANT_FALLBACK_LOCAL: bool = True

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-2.5-flash-lite,gemini-2.5-flash"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    FACE_MATCH_THRESHOLD: float = 0.70

    # Email OTP (Resend). Without RESEND_API_KEY, codes are logged server-side.
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "NetBot <onboarding@resend.dev>"
    EMAIL_OTP_EXPIRE_MINUTES: int = 10
    EMAIL_DEV_EXPOSE_CODE: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def gemini_model_list(self) -> list[str]:
        models = [self.GEMINI_MODEL.strip()]
        for name in self.GEMINI_FALLBACK_MODELS.split(","):
            name = name.strip()
            if name and name not in models:
                models.append(name)
        return models


settings = Settings()
