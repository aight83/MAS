import os
import uuid
import time
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB", "mas_db")]
collection = db["chat_history"]


async def init_db():
    # TTL
    await collection.create_index("ttl", expireAfterSeconds=0)
    # index full_name
    await collection.create_index([("full_name", 1), ("ttl", -1)])


async def save_log(
    chat_id: str,
    username: str,      
    query: str | None = None,
    answer: str | None = None,
    sources_links: list | None = None,
    time_taken: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_cost_usd: float | None = None,
    **kwargs,
):
    ttl = int(time.time()) + (7 * 24 * 60 * 60)
    await collection.insert_one({
        "dialog_id":    chat_id,
        "message_id":  f"{uuid.uuid4()}-{int(time.time())}",
        "full_name":    username,       
        "query":       query,
        "answer":      answer,
        "usage": {
            "input_tokens":   input_tokens,
            "output_tokens":  output_tokens,
            "total_cost_usd": total_cost_usd,
        },
        "sources_links": sources_links or [],
        "time_taken":   time_taken,
        "ttl":          ttl,
    })


async def get_history(chat_id: str, limit: int = 50) -> list:
    cursor = collection.find(
        {"dialog_id": chat_id},
        sort=[("ttl", 1)],
        limit=limit,
    )
    history = []
    async for doc in cursor:
        doc.pop("_id", None)
        history.append(doc)
    return history


async def get_user_chats(username: str) -> list:
    """Возвращает уникальные чаты пользователя — первый вопрос как preview."""
    pipeline = [
        {"$match": {"username": username}},
        {"$sort":  {"ttl": 1}},                    # хронологически
        {"$group": {                                 # группируем по chat_id
            "_id":        "$dialog_id",
            "preview":    {"$first": "$query"},     # первый вопрос
            "created_at": {"$first": "$ttl"},
        }},
        {"$sort": {"created_at": -1}},             # свежие сначала
        {"$limit": 20},
    ]
    result = []
    async for doc in collection.aggregate(pipeline):
        result.append({
            "chat_id":    doc["_id"],
            "preview":    (doc["preview"] or "")[:60] + "...",
            "created_at": doc["created_at"],
        })
    return result
