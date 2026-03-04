# backend/app/memory.py
import os
import uuid
import time
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB", "mas_db")]
collection = db["chat_history"]

async def save_log(
    chat_id: str,
    user_id: str | None = None,
    full_name: str | None = None,
    query: str | None = None,
    answer: str | None = None,
    sources_links: list | None = None,
    time_taken: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_cost_usd: float | None = None,
    **kwargs,
):
    ttl = int(time.time()) + (7 * 24 * 60 * 60)  # +7 дней
    doc = {
        "chat_id": chat_id,
        "user_id": user_id,
        "message_id": f"{uuid.uuid4()}-{int(time.time())}",
        "full_name": full_name,
        "query": query,
        "answer": answer,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": total_cost_usd,
        },
        "sources_links": sources_links,
        "time_taken": time_taken,
        "ttl": ttl,  # в MongoDB TTL настраивается через индекс
    }
    await collection.insert_one(doc)

async def get_history(chat_id: str, limit: int = 10) -> list:
    cursor = collection.find(
        {"chat_id": chat_id},
        sort=[("ttl", -1)],
        limit=limit,
    )
    history = []
    async for doc in cursor:
        doc.pop("_id", None)
        history.append(doc)
    return history
