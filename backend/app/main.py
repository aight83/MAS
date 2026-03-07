import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from .agents import orchestrator
from . import agents
from .memory import save_log, get_history, get_user_chats, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("MAS RAG System started")
    yield
    print("MAS RAG System stopped")


app = FastAPI(title="MAS RAG System", lifespan=lifespan)


# Schemas

class InvokeRequest(BaseModel):
    query: str
    chat_id: Optional[str] = None 

class InvokeResponse(BaseModel):
    response: str
    sources: list
    token_usage: dict
    chat_id: str
    time_taken: float

class ChatListItem(BaseModel):
    chat_id: str
    preview: str        # первый вопрос пользователя
    created_at: float   # timestamp


# Auth

def get_current_user(x_username: Optional[str] = Header(default=None)) -> str:
    """Просто берём имя из хедера. Без пароля — для демо."""
    if not x_username or not x_username.strip():
        raise HTTPException(status_code=401, detail="Header X-Username is required")
    return x_username.strip()


# Routes

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(
    request: InvokeRequest,
    x_username: Optional[str] = Header(default=None),
):
    username = get_current_user(x_username)

    chat_id = request.chat_id or str(uuid.uuid4())

    try:
        start = time.time()
        result = orchestrator(request.query)
        elapsed = time.time() - start

        msg = result.message
        content = msg.get("content", "") if isinstance(msg, dict) else msg
        if isinstance(content, list):
            response_text = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )
        else:
            response_text = str(content)

        usage = result.metrics.accumulated_usage
        token_usage = {
            "prompt_tokens":     usage.get("inputTokens", 0),
            "completion_tokens": usage.get("outputTokens", 0),
            "total_tokens":      usage.get("totalTokens", 0),
        }

        sources = agents._last_sources.copy()
        agents._last_sources.clear()

        await save_log(
            chat_id=chat_id,
            username=username,     
            query=request.query,
            answer=response_text,
            sources_links=sources,
            time_taken=elapsed,
            input_tokens=token_usage["prompt_tokens"],
            output_tokens=token_usage["completion_tokens"],
            total_cost_usd=0.0,
        )

        return InvokeResponse(
            response=response_text,
            sources=sources,
            token_usage=token_usage,
            chat_id=chat_id,
            time_taken=round(elapsed, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats", response_model=list[ChatListItem])
async def list_chats(x_username: Optional[str] = Header(default=None)):
    """Returns a list of user's chats with the first question as a preview."""
    username = get_current_user(x_username)
    return await get_user_chats(username)


@app.get("/history/{chat_id}")
async def get_chat_history(
    chat_id: str,
    x_username: Optional[str] = Header(default=None),
):
    """History of a specific chat."""
    get_current_user(x_username) 
    history = await get_history(chat_id)
    return {"chat_id": chat_id, "messages": history}
