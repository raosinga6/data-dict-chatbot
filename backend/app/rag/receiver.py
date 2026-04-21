import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from app.config import get_settings
from app.models.schemas import RetrievedContext

settings = get_settings()

_collection = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.HttpClient(host="localhost", port=8000)
        ef = OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small",
        )
        _collection = client.get_or_create_collection(
            name="data_dictionary",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def retrieve(question: str, schema_filter: str | None = None, top_k: int = 8) -> list[RetrievedContext]:
    where = {"schema_name": schema_filter.lower()} if schema_filter else None

    results = get_collection().query(
        query_texts=[question],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    contexts = []
    for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
        contexts.append(RetrievedContext(
            table_name=meta.get("table_name", ""),
            schema_name=meta.get("schema_name", ""),
            column_name=meta.get("column_name", ""),
            description=meta.get("description", ""),
            data_type=meta.get("data_type", ""),
            relevance_score=round(1 - dist, 4),   # cosine: 1=identical
        ))

    return contexts