from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    groq_model: str = "llama3-70b-8192"

    # Groq client resilience settings
    groq_timeout: int = 30
    groq_retries: int = 3
    groq_backoff: float = 1.0

    class Config:
        env_file = ".env"


settings = Settings()
