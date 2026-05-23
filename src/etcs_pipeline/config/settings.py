from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"


class EmbeddingProvider(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"


class GlobalConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    llm_provider: LLMProvider = LLMProvider.ANTHROPIC
    anthropic_api_key: str = Field(default="", repr=False)
    llm_api_key: str = Field(default="", repr=False)
    llm_base_url: str | None = None
    llm_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.1
    llm_max_tokens_planner: int = 4000
    llm_max_tokens_normalizer: int = 1000

    # Embedding
    embedding_provider: EmbeddingProvider = EmbeddingProvider.LOCAL
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "pipeline_db"
    db_user: str = "pipeline_user"
    db_password: str = Field(default="", repr=False)
    db_schema: str = "pipeline"

    # Profili
    profiles_root: str = "./profiles"
    active_profile: str = ""

    # Pipeline
    max_rerun_formal_validator: int = 3
    max_rerun_plausibility: int = 3

    # RAG
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 5

    # Cache
    cache_top_k: int = 3
    cache_similarity_threshold: float = 0.75

    # Logging
    log_level: str = "INFO"

    @property
    def db_connection_string(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} "
            f"dbname={self.db_name} user={self.db_user} "
            f"password={self.db_password}"
        )

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


_config: GlobalConfig | None = None


def get_config() -> GlobalConfig:
    global _config
    if _config is None:
        _config = GlobalConfig()
    return _config
