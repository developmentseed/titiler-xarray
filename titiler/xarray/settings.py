"""Titiler-xarray API settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class ApiSettings(BaseSettings):
    """FASTAPI application settings."""

    name: str = "titiler-xarray"
    cors_origins: str = "*"
    cors_allow_methods: str = "GET"
    cachecontrol: str = "public, max-age=3600"
    root_path: str = ""
    debug: bool = False

    model_config = SettingsConfigDict(env_prefix="TITILER_XARRAY_", env_file=".env")

    @field_validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    @field_validator("cors_allow_methods")
    def parse_cors_allow_methods(cls, v):
        """Parse CORS allowed methods."""
        return [method.strip().upper() for method in v.split(",")]

class CacheSettings(BaseSettings):
    """Cache settings"""

    endpoint: Optional[str] = None
    ttl: int = 3600
    namespace: str = ""

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "CACHE_"

cache_setting = CacheSettings()
