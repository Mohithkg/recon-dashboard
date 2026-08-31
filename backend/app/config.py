from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:aveto@localhost:5432/recon"
    JWT_SECRET: str = "dev-secret"
    OPENAI_API_KEY: str = ""


settings = Settings()
