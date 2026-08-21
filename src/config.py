from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    allowed_origin: str = "http://localhost:5173"
    peeringdb_api_key: str = ""
    redis_url: str | None = None
    port: int = 8080
    rate_limit_per_hour: int = 10
    ripestat_base_url: str = "https://stat.ripe.net/data/network-info/data.json"
    peeringdb_base_url: str = "https://www.peeringdb.com/api"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
