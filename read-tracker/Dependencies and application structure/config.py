from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="READING_TRACKER_")

    app_name: str = "Reading Tracker API"
    environment: Literal["development", "staging", "production"] = "development"
    docs_enabled: bool = True
    default_page_size: int = Field(default=10, ge=1, le=50)
    max_page_size: int = Field(default=50, ge=1, le=200)
    max_bulk_size: int = Field(default=20, ge=1, le=100)
    database_url: SecretStr


@lru_cache
def get_settings():
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
