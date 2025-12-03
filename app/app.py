#$~ Harmony Engine V3 ~$############################################################################################################################
#$~ Written by thedataguy ~$#
"""
There are redundant function definitions throughout the api routes, its done to keep all routes independent.
The idea is that at one point we can turn the api into microservices architecture without introducing complex interdependencies.
Along the same lines, Im trying out a architecture where the code block become self contained since its mostly by AI 
"""
import json

import tiktoken
from dotenv import load_dotenv
from fastapi import (
    FastAPI, HTTPException, Security, Depends,
    status, WebSocket, WebSocketDisconnect
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader

import app.core.chat.chat_pro as chat_pro
from app.constants import TOKEN_LIMIT, API_KEY, API_KEY_NAME
from app.api import codebase
from app.db.codebase import get_summary_from_db

load_dotenv()

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )

combined_app = FastAPI()
combined_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify allowed frontend origins
    allow_methods=["*"],
    allow_headers=["*"],
)
app = FastAPI(dependencies=[Depends(get_api_key)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(codebase.router, tags=["Codebase"])


#$~ Websocket 1 ~$############################################################################################################################
#$~ Description ~$#
"""
This websocket fetches the summary from DB and uses OpenAI Prompt caching to let users chat with the codebase.
The api feteches an existing chroma db collection under the project Id / Project Id and uses tool rag for generating answers
OpenAI is used for chat. The response is returned in stream.
Message History - Last 5 turns of the conversation.
"""
@combined_app.websocket("/chat-pro")
async def chat_pro_version (websocket: WebSocket):
    await websocket.accept()
    try:
        # 1. Receive JSON payload from frontend
        data = await websocket.receive_json()
        user_question = data.get("user_question", "")
        project_id = data.get("project_id")
        email = data.get("email")
        checklistAssistant = data.get("checklistAssistant", False)
        uploaded_files_raw = data.get("uploaded_files")

        # Always convert to a Python list
        if not uploaded_files_raw:
            uploaded_files = []
        elif isinstance(uploaded_files_raw, str):
            try:
                parsed = json.loads(uploaded_files_raw)
                uploaded_files = parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                uploaded_files = []
        elif isinstance(uploaded_files_raw, list):
            uploaded_files = uploaded_files_raw
        else:
            uploaded_files = []

        async def on_stream(content_chunk: str):
            await websocket.send_text(content_chunk)

        # Fetch summary from PostgreSQL
        summary_content = await get_summary_from_db(email, project_id)
        if not summary_content:
            raise HTTPException(status_code=404, detail="Summary not found")
        
        enc = tiktoken.encoding_for_model("gpt-4")  # Modify as needed for Anthropic
        tokens = enc.encode(summary_content)
        token_count = len(tokens)
        if token_count > TOKEN_LIMIT:
            truncated_tokens = tokens[:TOKEN_LIMIT]
            summary_content = enc.decode(truncated_tokens)


    except Exception as e:
        await websocket.send_text(f"[ERROR] Failed to read summary: {str(e)}")
    try:
        await chat_pro.chat(email, project_id, summary_content, user_question, checklistAssistant, uploaded_files, on_stream)

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        await websocket.send_text(f"[ERROR] {str(e)}")
    finally:
        await websocket.close()

############################################################################################################################

combined_app.mount("/", app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(combined_app, host="0.0.0.0", port=8000)
