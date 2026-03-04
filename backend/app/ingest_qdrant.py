from dotenv import load_dotenv
load_dotenv()

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.models import SparseVectorParams, SparseIndexParams
import uuid
from qdrant_client.models import models as qmodels
from fastembed import TextEmbedding


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

COLLECTION_NAME = "knowledge_base"

# Тестовые документы — FAQ и политики магазина
DOCUMENTS = [
    {
        "id": str(uuid.uuid4()),
        "text": "Возврат товара возможен в течение 14 дней с момента покупки. "
                "Товар должен быть в оригинальной упаковке и без следов использования. "
                "Для оформления возврата обратитесь в службу поддержки с номером заказа.",
        "metadata": {"type": "policy", "title": "Политика возврата"}
    },
    {
        "id": str(uuid.uuid4()),
        "text": "Доставка осуществляется по всему Казахстану. "
                "Стандартная доставка занимает 3-5 рабочих дней. "
                "Экспресс-доставка доступна в Алматы и Астане — 1-2 дня. "
                "Доставка бесплатна при заказе от 50000 тенге.",
        "metadata": {"type": "policy", "title": "Условия доставки"}
    },
    {
        "id": str(uuid.uuid4()),
        "text": "MacBook Pro — профессиональный ноутбук Apple с процессором M3 Pro. "
                "Оснащён дисплеем Liquid Retina XDR 16 дюймов, до 36 ГБ оперативной памяти "
                "и батареей до 22 часов работы. Идеален для разработки, видеомонтажа и дизайна.",
        "metadata": {"type": "product", "title": "MacBook Pro"}
    },
    {
        "id": str(uuid.uuid4()),
        "text": "iPhone 15 оснащён чипом A16 Bionic, камерой 48 МП и Dynamic Island. "
                "Поддерживает USB-C зарядку и передачу данных. "
                "Доступен в цветах: чёрный, синий, розовый, жёлтый, зелёный.",
        "metadata": {"type": "product", "title": "iPhone 15"}
    },
    {
        "id": str(uuid.uuid4()),
        "text": "Гарантия на все товары составляет 12 месяцев с момента покупки. "
                "Гарантийный ремонт осуществляется бесплатно при наличии заводского брака. "
                "Физические повреждения и залитие жидкостью под гарантию не попадают.",
        "metadata": {"type": "policy", "title": "Гарантийные условия"}
    },
    {
        "id": str(uuid.uuid4()),
        "text": "Наушники Sony WH-1000XM5 с активным шумоподавлением. "
                "До 30 часов работы от аккумулятора, быстрая зарядка 10 минут = 5 часов работы. "
                "Поддержка Hi-Res Audio, LDAC и мультиподключения к двум устройствам.",
        "metadata": {"type": "product", "title": "Наушники Sony"}
    },
]
def ingest():
    import time
    client = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), port=int(os.getenv("QDRANT_PORT", 6333)))

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

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    # Вычисляем эмбеддинги
    embedder = TextEmbedding(MODEL_NAME)
    texts = [doc["text"] for doc in DOCUMENTS]
    embeddings = list(embedder.embed(texts))

    # Создаём коллекцию вручную
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=len(embeddings[0]), distance=Distance.COSINE),
    )

    # Загружаем точки
    points = [
        PointStruct(
            id=doc["id"],
            vector=embeddings[i].tolist(),
            payload={"document": doc["text"], **doc["metadata"]},
        )
        for i, doc in enumerate(DOCUMENTS)
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)

    count = client.count(collection_name=COLLECTION_NAME)
    print(f"Ingested. Total: {count.count} docs.")

if __name__ == "__main__":
    ingest()
