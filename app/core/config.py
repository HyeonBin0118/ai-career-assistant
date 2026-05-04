from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "mock_interview"


    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()