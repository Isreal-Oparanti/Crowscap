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
    qwen_fast_model: str = "qwen-turbo"
    qwen_chat_model: str = "qwen-plus"
    qwen_extraction_model: str = "qwen-plus"
    qwen_relationship_model: str = "qwen-turbo"
    qwen_embedding_model: str = "text-embedding-v4"
    qwen_rerank_model: str = "qwen3-rerank"
    qwen_belief_audit_model: str = "qwen-plus"

    relationship_candidate_min_score: float = 0.50
    relationship_candidate_limit: int = 3
    relationship_pair_limit: int = 4
    relationship_near_duplicate_max_score: float = 0.75
    relationship_timeout_seconds: float = 20.0
    relationship_max_retries: int = 0

    recall_due_limit: int = 50

    public_search_provider: Literal["auto", "disabled", "jina", "duckduckgo"] = "auto"
    public_search_base_url: str = "https://s.jina.ai/"
    public_search_duckduckgo_url: str = "https://html.duckduckgo.com/html/"
    public_search_timeout_seconds: float = 10.0

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
