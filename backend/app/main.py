import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .memory import save_log, get_history
from .agents import orchestrator
from . import agents

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("MAS RAG System started")
    yield
    print("MAS RAG System stopped")

app = FastAPI(title="MAS RAG System", lifespan=lifespan)

# ─── Schemas ──────────────────────────────────────────────────────────────────

class InvokeRequest(BaseModel):
    query: str
    chat_id: str = None
    user_id: str = None

class InvokeResponse(BaseModel):
    response: str
    sources: list
    token_usage: dict
    chat_id: str
    time_taken: float

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(request: InvokeRequest):
    chat_id = request.chat_id or str(uuid.uuid4())
    user_id = request.user_id or str(uuid.uuid4())

    try:
        start = time.time()
        result = orchestrator(request.query)
        elapsed = time.time() - start

        # ✅ Правильное извлечение текста
        msg = result.message
        content = msg.get("content", "")
        if isinstance(content, list):
            response_text = " ".join(
                block.get("text", "") for block in content if isinstance(block, dict)
            )
        else:
            response_text = str(content)

        # Токены
        usage = result.metrics.accumulated_usage
        input_tokens  = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        total_tokens  = usage.get("totalTokens", 0)

        token_usage = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

        sources = agents._last_sources.copy()
        agents._last_sources.clear()
        print(f">>> sources in response: {sources}")
    
    
        await save_log(
            chat_id=chat_id,
            user_id=user_id,
            full_name="demo_user",
            query=request.query,
            answer=response_text,
            sources_links=sources,
            time_taken=elapsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
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


@app.get("/history/{chat_id}")
async def get_chat_history(chat_id: str):
    history = await get_history(chat_id)
    return {"chat_id": chat_id, "messages": history}
