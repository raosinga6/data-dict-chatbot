from openai import OpenAI
import chromadb
from app.config import get_settings
from app.models.schemas import RetrievedContext
from sentence_transformers import SentenceTransformer
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed(texts: list[str]) -> list[list[float]]:
    return _model.encode(texts, show_progress_bar=False).tolist()

settings = get_settings()
openai_client = OpenAI(api_key=settings.openai_api_key)
_collection = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.HttpClient(host="localhost", port=8001)
        _collection = client.get_or_create_collection(
            name="data_dictionary",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection

def retrieve(question: str, schema_filter: str | None = None, top_k: int = 8) -> list[RetrievedContext]:
    try:
        '''
        embedding = openai_client.embeddings.create(
            input=[question],
            model="text-embedding-3-small",
        ).data[0].embedding
        '''

        embedding = _model.encode([question]).tolist()[0]

        where = {"schema_name": schema_filter.lower()} if schema_filter else None
        results = get_collection().query(
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