from dotenv import load_dotenv
import os
import re
import psycopg2
import boto3
from qdrant_client import models as qdrant_models
from qdrant_client import QdrantClient
from qdrant_client.models import SearchRequest
from strands.models import BedrockModel
from strands import Agent, tool
from strands.models.litellm import LiteLLMModel
from qdrant_client import models
from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embedder = TextEmbedding(MODEL_NAME)
_last_sources: list[str] = [] 

load_dotenv()

# model = BedrockModel(
#     model_id="anthropic.claude-3-haiku-20240307-v1:0",
#     region_name="us-east-1",
#     temperature=0.1,
# )


model = LiteLLMModel(
    model_id="openai/gpt-oss-120b",  # Используем openai/ префикс
    params={
        "api_key": os.getenv("AI_STUDIO_API_KEY"),
        "api_base": "https://api.cerebras.ai/v1",
        "max_tokens": 3000,           # Строгий лимит на генерацию в 1 запросе (хватит для ответа и тулов)
        "temperature": 0.1            # Снижаем креативность, чтобы агент не галлюцинировал
    }
)




# ─── RAG Agent ────────────────────────────────────────────────────────────────

qdrant = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333)),
)

COLLECTION_NAME = "knowledge_base"

@tool
def search_knowledge_base(query: str) -> str:
    global _last_sources
    try:
        query_vector = list(embedder.embed([query]))[0].tolist()
        results = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=3,
            with_payload=True,
        ).points
        if not results:
            return "No relevant documents found."

        _last_sources = list({r.payload.get("title", "unknown") for r in results})
        print(f">>> _last_sources set: {_last_sources}")  # проверка

        return "\n\n".join([
            f"[Source {i+1}] ({r.payload.get('title', 'unknown')}): {r.payload.get('document', '')}"
            for i, r in enumerate(results)
        ])
    except Exception as e:
        print(f">>> [search_knowledge_base] ERROR: {e}")
        return f"Knowledge base unavailable: {str(e)}"



    
rag_agent = Agent(
    model=model,
    system_prompt="""You are a strict Retrieval-Augmented Generation (RAG) assistant.
        Your ONLY source of knowledge is the `search_knowledge_base` tool.

        Rules:
        1. ALWAYS call `search_knowledge_base` first before answering.
        2. NEVER use your internal knowledge or make assumptions.
        3. If the tool returns "No relevant documents found", reply EXACTLY: "I cannot find the answer in the knowledge base."
        4. Base your answer STRICTLY and ONLY on the tool's returned text.
        5. Output ONLY the answer. Do NOT append source tags, citations, or any metadata.
        """,
    tools=[search_knowledge_base],
)


# ─── Text2SQL Agent ───────────────────────────────────────────────────────────
def get_pg_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", 5432),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

def _extract_tables_from_sql(sql: str) -> list[str]:
    """Извлекает имена таблиц из SQL-запроса через FROM и JOIN."""
    # Ищем слова после FROM и JOIN (LEFT/RIGHT/INNER/OUTER JOIN тоже)
    pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    tables = re.findall(pattern, sql, re.IGNORECASE)
    return list(set(tables))  # убираем дубли


@tool
def get_db_schema() -> str:
    """Returns the names of all tables and columns in the SQL database."""
    schema = """
    Tables available:
    - users(id, full_name, email, created_at)
    - transactions(id, user_id, amount, status, created_at)
    - product_catalog(id, name, description, price, category)
    """
    return schema
@tool
def execute_sql(sql_query: str) -> str:
    """Executes a PostgreSQL SELECT query and returns the real data from the database."""
    global _last_sources
    print(f">>> [execute_sql] CALLED WITH: {sql_query}")
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        if not sql_query.strip().upper().startswith("SELECT"):
            return "Error: only SELECT queries are allowed."

        cur.execute(sql_query)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        # ✅ Трекаем таблицы — аналогично _last_sources в RAG
        tables = _extract_tables_from_sql(sql_query)
        _last_sources = [f"sql:{t}" for t in tables]
        print(f">>> _last_sources set: {_last_sources}")

        if not rows:
            return "Query returned no results."

        result = " | ".join(columns) + "\n"
        result += "\n".join([" | ".join(str(v) for v in row) for row in rows])
        return result

    except Exception as e:
        return f"SQL Error: {str(e)}"
    
sql_agent = Agent(
    model=model,
    system_prompt="""You are a strict Text2SQL data analyst.

CRITICAL PROCESS:
Step 1: ALWAYS call `get_db_schema` to learn available tables.
Step 2: Write a valid PostgreSQL `SELECT` query based ONLY on the schema.
Step 3: ALWAYS call `execute_sql` passing your query.
Step 4: Return the results to the user.

Rules:
- NEVER guess column names. If it's not in the schema, you cannot query it.
- NEVER invent or simulate query results. You MUST call `execute_sql` and wait for the real data.
- If `execute_sql` returns an error, fix the SQL and try again (max 2 retries).

Format your final response simply, including the data you found.""",
    tools=[get_db_schema, execute_sql],
)


# ─── Orchestrator Agent ───────────────────────────────────────────────────────

@tool
def delegate_to_rag(query: str) -> str:
    """Routes the query to the RAG agent. Returns a plain-text answer based strictly on the knowledge base."""
    result = rag_agent(query)
    msg = result.message
    content = msg.get("content", "") if isinstance(msg, dict) else msg
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return str(content)

@tool
def delegate_to_sql(query: str) -> str:
    """Routes the query to the SQL agent. Returns tabular data retrieved from the database."""
    result = sql_agent(query)
    msg = result.message
    content = msg.get("content", "") if isinstance(msg, dict) else msg
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return str(content)

orchestrator = Agent(
    model=model,
    system_prompt="""You are the Orchestrator Router. Your job is to delegate user queries to the correct sub-agent.

Available Agents:
- `delegate_to_sql`: Use this for questions about users, transactions, products, prices, or counts (e.g., "How many users?", "Show me transactions").
- `delegate_to_rag`: Use this for questions about company policies, documents, guides, or general text knowledge.

Rules:
1. Analyze the user's prompt.
2. IMMEDIATELY call the appropriate tool (`delegate_to_sql` OR `delegate_to_rag`).
3. DO NOT explain your reasoning before calling the tool.
4. When the tool returns data, output that exact data as your final answer. Do not add conversational filler.
""",
    tools=[delegate_to_rag, delegate_to_sql],
)

