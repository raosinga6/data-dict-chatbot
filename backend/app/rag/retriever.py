from app.config import get_settings
from app.models.schemas import RetrievedContext

settings = get_settings()
_model = None
_collection = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_collection():
    global _collection
    if _collection is None:
        try:
            import chromadb
            client = chromadb.HttpClient(host="localhost", port=8001)
            _collection = client.get_or_create_collection(
                name="data_dictionary",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            return None
    return _collection


def retrieve(question: str, schema_filter: str | None = None, top_k: int = 8) -> list[RetrievedContext]:
    try:
        collection = get_collection()
        if collection is None:
            return []
        embedding = get_model().encode([question]).tolist()[0]
        where = {"schema_name": schema_filter.lower()} if schema_filter else None
        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["metadatas", "distances"],
        )
        return [
            RetrievedContext(
                table_name=meta.get("table_name", ""),
                schema_name=meta.get("schema_name", ""),
                column_name=meta.get("column_name", ""),
                description=meta.get("description", ""),
                data_type=meta.get("data_type", ""),
                relevance_score=round(1 - dist, 4),
            )
            for meta, dist in zip(results["metadatas"][0], results["distances"][0])
        ]
    except Exception:
        return []
