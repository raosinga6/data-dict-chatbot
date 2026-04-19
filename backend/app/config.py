from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# backend/app/config.py is 3 levels below repo root:
# data-dict-chatbot/backend/app/config.py → parents[2] = data-dict-chatbot/
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # App
    app_name: str = "Data Dictionary Chatbot"
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection: str = "data_dictionary"

    # Redis
    redis_url: str = "redis://redis:6379"
    session_ttl_seconds: int = 1800

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    llm_temperature: float = 0.0
    max_retrieved_docs: int = 5

    # SQL safety
    sql_max_rows: int = 1000
    blocked_sql_keywords: list[str] = [
        "INSERT", "UPDATE", "DELETE", "DROP",
        "TRUNCATE", "ALTER", "CREATE", "GRANT",
        "REVOKE", "EXECUTE",
    ]

    # Streamlit
    # api_base_url: str = "http://backend:8000/api/v1"
    api_base_url: str = "http://backend:8000/api/v1" 
    

    model_config = {
        "env_file": str(_REPO_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()