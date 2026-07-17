from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

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

    crowscap_mcp_enabled: bool = False
    crowscap_mcp_host: str = "127.0.0.1"
    crowscap_mcp_port: int = 8010
    crowscap_mcp_transport: Literal["stdio", "sse", "streamable-http"] = "sse"
    crowscap_mcp_sse_path: str = "/mcp/sse"
    crowscap_mcp_message_path: str = "/mcp/messages/"
    crowscap_mcp_streamable_http_path: str = "/mcp"
    crowscap_proxy_secret: SecretStr | None = Field(default=None)
    crowscap_auth_required: bool = True
    crowscap_dev_user_id: str = "dev_local_user"
    crowscap_dev_user_email: str = "dev@crowscap.local"

    @property
    def has_qwen_key(self) -> bool:
        return bool(self.dashscope_api_key_value)

    @property
    def dashscope_api_key_value(self) -> str | None:
        if self.dashscope_api_key is None:
            return None
        value = self.dashscope_api_key.get_secret_value().strip()
        return value or None

    @property
    def crowscap_proxy_secret_value(self) -> str | None:
        if self.crowscap_proxy_secret is None:
            return None
        value = self.crowscap_proxy_secret.get_secret_value().strip()
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def mask_url_credentials(url: str) -> str:
    """Hide password-like credentials before writing connection URLs to logs."""
    parsed = urlsplit(url)
    if not parsed.netloc or "@" not in parsed.netloc:
        return url

    userinfo, hostinfo = parsed.netloc.rsplit("@", 1)
    if ":" in userinfo:
        username, _password = userinfo.split(":", 1)
        safe_userinfo = f"{username}:***"
    else:
        safe_userinfo = "***"

    return urlunsplit(
        (
            parsed.scheme,
            f"{safe_userinfo}@{hostinfo}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
