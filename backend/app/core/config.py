from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Crowscap API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./crowscap_dev.db"

    dashscope_api_key: SecretStr | None = Field(default=None)
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_reasoning_model: str = "qwen3.7-plus"
    qwen_fast_model: str = "qwen3.6-flash"
    qwen_embedding_model: str = "text-embedding-v4"
    qwen_rerank_model: str = "qwen3-rerank"

    relationship_candidate_min_score: float = 0.30
    relationship_candidate_limit: int = 5

    @property
    def has_qwen_key(self) -> bool:
        return bool(self.dashscope_api_key_value)

    @property
    def dashscope_api_key_value(self) -> str | None:
        if self.dashscope_api_key is None:
            return None
        value = self.dashscope_api_key.get_secret_value().strip()
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
