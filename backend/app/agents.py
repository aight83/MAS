from dotenv import load_dotenv
import os
import psycopg2
import boto3
from qdrant_client import QdrantClient
from qdrant_client.models import SearchRequest
from strands.models import BedrockModel
from strands import Agent, tool
from strands.models.litellm import LiteLLMModel

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
    """Searches the vector database for text documents, policies, and guides. Input should be a short search query."""
    try:
        # Dense search
        results = qdrant.query(
            collection_name=COLLECTION_NAME,
            query_text=query,
            limit=3,
        )
        if not results:
            return "No relevant documents found."
        return "\n\n".join([
            f"[Source {i+1}]: {r.document}" 
            for i, r in enumerate(results)
        ])
    except Exception as e:
        return f"Knowledge base unavailable: {str(e)}"
    
rag_agent = Agent(
    model=model,
    system_prompt="""You are a strict Retrieval-Augmented Generation (RAG) assistant.
Your ONLY source of knowledge is the `search_knowledge_base` tool.

Rules:
1. ALWAYS call `search_knowledge_base` first.
2. NEVER use your internal knowledge.
3. If the tool returns "No relevant documents found", reply exactly: "I cannot find the answer in the knowledge base."
4. Base your answer STRICTLY on the tool's output.

Output your final answer directly, followed by a list of sources used (e.g. "[Source 1]").""",
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
    """Executes a PostgreSQL SELECT query and returns the real data from the database. Input MUST be a valid SQL string."""
    print(f">>> [execute_sql] CALLED WITH: {sql_query}")  
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        # Safety: only SELECT
        if not sql_query.strip().upper().startswith("SELECT"):
            return "Error: only SELECT queries are allowed."
        cur.execute(sql_query)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
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
    """Call the RAG agent and return its structured plain-text output.

    Guidance: return the RAG agent's answer exactly as produced, including
    the `Sources:` and `Confidence:` sections.
    """
    result = rag_agent(query)
    return result.message

@tool
def delegate_to_sql(query: str) -> str:
    """Call the SQL agent and return its structured plain-text output.

    Guidance: return the SQL statement and the tabular results as the agent
    produces them, and include any `Notes:` the agent supplies.
    """
    result = sql_agent(query)
    return result.message

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

