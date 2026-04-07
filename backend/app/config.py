from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-haiku"


settings = Settings()
