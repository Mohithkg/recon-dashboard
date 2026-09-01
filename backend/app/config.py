from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required: no default.  Deployment must set this or the app refuses to start.
    JWT_SECRET: str
    OPENAI_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/recon"


settings = Settings()
