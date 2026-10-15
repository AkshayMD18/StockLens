from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_PROVIDER = "ollama"
GROQ_PROVIDER = "groq"


class Settings(BaseSettings):
    database_url: str = Field(default="")
    groq_api_key: SecretStr | None = None
    stock_data: SecretStr | None = None
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
