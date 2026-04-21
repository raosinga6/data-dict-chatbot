from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# backend/app/config.py is 3 levels below repo root:
# data-dict-chatbot/backend/app/config.py → parents[2] = data-dict-chatbot/
_REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/app/ → backend/ → data-dict-chatbot/


class Settings(BaseSettings):
    # App
    app_name: str = "Data Dictionary Chatbot"
    environment: str = "development"
    log_level: str = "INFO"
 
    # Database
    database_url: str

    # ChromaDB
    chroma_url: str = "http://chromadb:8000"
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection: str = "data_dictionary"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    session_ttl_seconds: int = 1800
    allowed_origins: list[str] = ["http://localhost:8501"]

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
    

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",          # silently ignore unknown env vars
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
