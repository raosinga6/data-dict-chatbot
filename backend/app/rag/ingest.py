import asyncio
import hashlib
from openai import OpenAI
import chromadb
from app.config import get_settings
from app.models.db import get_session_factory
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed(texts: list[str]) -> list[list[float]]:
    return _model.encode(texts, show_progress_bar=False).tolist()

settings = get_settings()
openai_client = OpenAI(api_key=settings.openai_api_key)

def get_chroma_collection():
    client = chromadb.HttpClient(host="localhost", port=8001)
    # no embedding function — we embed manually
    return client.get_or_create_collection(
        name="data_dictionary",
        metadata={"hnsw:space": "cosine"},
    )
'''
def embed(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )
    return [r.embedding for r in response.data]
'''
async def ingest():
    factory = get_session_factory()
    collection = get_chroma_collection()

    async with factory() as db:
        tables = (await db.execute(text(
            "SELECT schema_name, table_name, description FROM dd_tables"
        ))).mappings().all()

        columns = (await db.execute(text("""
            SELECT c.schema_name, c.table_name, c.column_name,
                   c.data_type, c.description,
                   c.is_primary_key, c.is_foreign_key,
                   c.references_table, c.references_column
            FROM dd_columns c
        """))).mappings().all()

    documents, ids, metadatas = [], [], []

    for t in tables:
        row = dict(t)
        doc = build_document(row)
        uid = hashlib.md5(f"table::{row['schema_name']}.{row['table_name']}".encode()).hexdigest()
        documents.append(doc)
        ids.append(uid)
        metadatas.append({
            "type": "table",
            "schema_name": row["schema_name"],
            "table_name": row["table_name"],
        })

    for c in columns:
        row = dict(c)
        doc = build_document(row)
        uid = hashlib.md5(
            f"col::{row['schema_name']}.{row['table_name']}.{row['column_name']}".encode()
        ).hexdigest()
        documents.append(doc)
        ids.append(uid)
        metadatas.append({
            "type": "column",
            "schema_name": row["schema_name"],
            "table_name": row["table_name"],
            "column_name": row["column_name"],
        })

    # embed + upsert in batches of 100
    batch = 100
    for i in range(0, len(documents), batch):
        batch_docs = documents[i:i+batch]
        batch_ids = ids[i:i+batch]
        batch_meta = metadatas[i:i+batch]
        embeddings = embed(batch_docs)
        collection.upsert(
            documents=batch_docs,
            embeddings=embeddings,
            ids=batch_ids,
            metadatas=batch_meta,
        )
        print(f"Upserted {min(i+batch, len(documents))}/{len(documents)}")

    print(f"Done. {len(documents)} documents in ChromaDB.")

def build_document(row: dict) -> str:
    parts = [
        f"Table: {row['schema_name']}.{row['table_name']}",
        f"Column: {row['column_name']}" if row.get('column_name') else "",
        f"Type: {row.get('data_type', '')}",
        f"Description: {row.get('description', '')}",
        f"Primary key: {row.get('is_primary_key', False)}",
        f"Foreign key: {row.get('is_foreign_key', False)}",
        f"References: {row.get('references_table', '')}.{row.get('references_column', '')}"
        if row.get('references_table') else "",
    ]
    return " | ".join(p for p in parts if p)
if __name__ == "__main__":
    asyncio.run(ingest())