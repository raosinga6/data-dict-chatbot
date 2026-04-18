from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Data Dictionary Chatbot"
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection: str = "data_dictionary"

    # Redis
    redis_url: str = "redis://redis:6379"
    session_ttl_seconds: int = 1800  # 30 minutes

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    llm_temperature: float = 0.0   # deterministic — critical for SQL
    max_retrieved_docs: int = 5

    # SQL safety
    sql_max_rows: int = 1000
    blocked_sql_keywords: list[str] = [
        "INSERT", "UPDATE", "DELETE", "DROP",
        "TRUNCATE", "ALTER", "CREATE", "GRANT",
        "REVOKE", "EXECUTE",
    ]

    # Streamlit
    api_base_url: str = "http://localhost:8000/api/v1"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()