from dotenv import load_dotenv
import boto3

from fastapi import FastAPI, HTTPException

from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime, timezone

from strands import Agent
from strands.models import BedrockModel

load_dotenv()

app = FastAPI(title="Strands Agent Server", version="1.0.0")

# Note: Any supported model provider can be configured
# Automatically uses process.env.OPENAI_API_KEY
bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1"  # change if needed
)

model = BedrockModel(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-west-2",
    temperature=0.3,
)

strands_agent = Agent(model=model)

class InvocationRequest(BaseModel):
    input: Dict[str, Any]

class InvocationResponse(BaseModel):
    output: Dict[str, Any]

@app.post("/invocations", response_model=InvocationResponse)
async def invoke_agent(request: InvocationRequest):
    try:
        user_message = request.input.get("prompt", "")
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="No prompt found in input. Please provide a 'prompt' key in the input."
            )

        result = strands_agent(user_message)
        response = {
            "message": result.message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": "strands-agent",
        }

        return InvocationResponse(output=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")

@app.get("/ping")
async def ping():
    return {"status": "healthy"}

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()