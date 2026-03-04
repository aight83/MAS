from dotenv import load_dotenv
load_dotenv()

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.models import SparseVectorParams, SparseIndexParams
import uuid

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
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
    )

    # Создаём коллекцию если не существует
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' already exists, deleting...")
        client.delete_collection(COLLECTION_NAME)

    # Создаём коллекцию с dense векторами
    # Qdrant FastEmbed автоматически создаёт эмбеддинги через query()
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=384,           # размер вектора для модели all-MiniLM-L6-v2
            distance=Distance.COSINE,
        ),
    )
    print(f"Collection '{COLLECTION_NAME}' created.")

    # Загружаем документы через add() — он сам создаёт эмбеддинги
    client.add(
        collection_name=COLLECTION_NAME,
        documents=[doc["text"] for doc in DOCUMENTS],
        metadata=[doc["metadata"] for doc in DOCUMENTS],
        ids=[doc["id"] for doc in DOCUMENTS],
    )

    print(f"Ingested {len(DOCUMENTS)} documents into '{COLLECTION_NAME}'.")
    
    # Проверка
    count = client.count(collection_name=COLLECTION_NAME)
    print(f"Total documents in collection: {count.count}")

if __name__ == "__main__":
    ingest()
