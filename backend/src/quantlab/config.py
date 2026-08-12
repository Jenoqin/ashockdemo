from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    tushare_token: str | None = Field(default=None, validation_alias="TUSHARE_TOKEN")
    database_path: str = Field(default="./data/quantlab.db", validation_alias="QUANTLAB_DATABASE_PATH")
    demo_mode: bool = Field(default=False, validation_alias="QUANTLAB_DEMO_MODE")
    frontend_origin: str = Field(default="http://localhost:5173", validation_alias="QUANTLAB_FRONTEND_ORIGIN")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
