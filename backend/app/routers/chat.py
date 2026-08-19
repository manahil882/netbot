from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google.genai import types
from app.services.gemini import client
from app.services.supabase import supabase

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str

@router.post("/")
async def chat_endpoint(req: ChatRequest):
    try:
        # 1. Fetch conversation history from Supabase
        history_res = supabase.table("chat_history") \
            .select("role, content") \
            .eq("session_id", req.session_id) \
            .order("created_at") \
            .execute()
        
        # 2. Format history for GenAI SDK
        contents = []
        for msg in history_res.data:
            contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=req.message)]))

        # 3. Request generation from Gemini 2.5 Flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )
        reply_text = response.text

        # 4. Save updated turn back to Supabase
        supabase.table("chat_history").insert([
            {"session_id": req.session_id, "user_id": req.user_id, "role": "user", "content": req.message},
            {"session_id": req.session_id, "user_id": req.user_id, "role": "model", "content": reply_text}
        ]).execute()

        return {"response": reply_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))