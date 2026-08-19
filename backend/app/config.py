from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str  # must be the service_role key, not anon, since the backend
                        # reads/writes profiles and document_chunks directly (RLS bypass)
    GEMINI_API_KEY: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24h

    class Config:
        env_file = ".env"


settings = Settings()
