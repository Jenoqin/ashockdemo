from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

class Settings(BaseSettings):
    tushare_token: str | None = Field(default=None, validation_alias="TUSHARE_TOKEN")
    tushare_token_file: str | None = Field(default=None, validation_alias="TUSHARE_TOKEN_FILE")
    tushare_api_url: str = Field(default="https://api.waditu.com/dataapi", validation_alias="TUSHARE_API_URL")
    database_path: str = Field(default="./data/quantlab-hfq-v1.db", validation_alias="QUANTLAB_DATABASE_PATH")
    demo_database_path: str = Field(default="./data/quantlab-demo-v2.db", validation_alias="QUANTLAB_DEMO_DATABASE_PATH")
    demo_mode: bool = Field(default=False, validation_alias="QUANTLAB_DEMO_MODE")
    frontend_origin: str = Field(default="http://localhost:5173", validation_alias="QUANTLAB_FRONTEND_ORIGIN")
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
