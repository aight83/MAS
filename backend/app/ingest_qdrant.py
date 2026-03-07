from dotenv import load_dotenv
load_dotenv()
from pathlib import Path

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, SparseVector, VectorParams, PointStruct
from qdrant_client.models import SparseVectorParams, SparseIndexParams
import uuid
from qdrant_client.models import models as qmodels
from fastembed import TextEmbedding, SparseTextEmbedding
from qdrant_client.models import (
    VectorParams, Distance, SparseVectorParams, SparseIndexParams
)


DENSE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SPARSE_MODEL = "Qdrant/bm25"
sparse_embedder = SparseTextEmbedding(SPARSE_MODEL)

COLLECTION_NAME = "knowledge_base"

from dotenv import load_dotenv
load_dotenv()

import os
import uuid
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, SparseVector, VectorParams, PointStruct,
    SparseVectorParams, SparseIndexParams
)
from fastembed import TextEmbedding, SparseTextEmbedding

DENSE_MODEL  = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SPARSE_MODEL = "Qdrant/bm25"
COLLECTION_NAME = "knowledge_base"
DATA_DIR = os.getenv("DATA_DIR", "/app/data")


# Hardcoded for fallback

HARDCODED_DOCUMENTS = [
    {
        "text": "Возврат товара возможен в течение 14 дней...",
        "source": "hardcoded",
        "title": "Политика возврата",
        "type": "policy",
    },
]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def load_from_directory(data_dir: str) -> list[dict]:
    path = Path(data_dir)
    print(f">>> DATA_DIR = {data_dir}")
    print(f">>> Path exists: {path.exists()}")

    if not path.exists():
        print("DATA_DIR не найден")
        return []

    all_files = list(path.rglob("*.txt")) + list(path.rglob("*.md"))
    print(f">>> Files found: {[f.name for f in all_files]}")

    result = []
    for file in all_files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text)
        for chunk in chunks:
            result.append({
                "text":   chunk,
                "source": str(file),
                "title":  file.stem,
            })
        print(f"  ✅ {file.name} → {len(chunks)} чанков")

    print(f">>> Total chunks from files: {len(result)}")
    return result


def ingest():
    import time
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )

    for attempt in range(10):
        try:
            client.get_collections()
            print("Qdrant is ready.")
            break
        except Exception:
            print(f"Waiting for Qdrant... ({attempt + 1}/10)")
            time.sleep(3)
    else:
        raise RuntimeError("Qdrant not available")

    # Documents to ingest
    file_docs = load_from_directory(DATA_DIR)

    hardcoded = [
        {"text": d["text"], "source": d["source"], "title": d["title"]}
        for d in HARDCODED_DOCUMENTS
    ]

    all_docs = file_docs + hardcoded
    print(f"📊 Итого к индексации: {len(all_docs)} чанков")

    # Embeddings
    dense_embedder  = TextEmbedding(DENSE_MODEL)
    sparse_embedder = SparseTextEmbedding(SPARSE_MODEL)

    texts             = [d["text"] for d in all_docs]
    dense_embeddings  = list(dense_embedder.embed(texts))
    sparse_embeddings = list(sparse_embedder.embed(texts))

    # Collection setup
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(size=len(dense_embeddings[0]), distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
        },
    )

    # Loading points
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector={
                "dense": dense_embeddings[i].tolist(),
                "sparse": SparseVector(
                    indices=sparse_embeddings[i].indices.tolist(),
                    values=sparse_embeddings[i].values.tolist(),
                ),
            },
            payload={
                "document":  doc["text"],
                "title":     doc["title"],
                "file_path": doc["source"],
            },
        )
        for i, doc in enumerate(all_docs)
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)

    count = client.count(collection_name=COLLECTION_NAME)
    print(f"✅ Ingested {count.count} docs with dense + sparse vectors")


if __name__ == "__main__":
    ingest()
