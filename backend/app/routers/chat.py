from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google.genai import types

from app.services.gemini import client
from app.services.supabase import supabase
from app.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/")
async def chat_endpoint(req: ChatRequest, user=Depends(get_current_user)):
    try:
        history_res = (
            supabase.table("chat_history")
            .select("role, content")
            .eq("session_id", req.session_id)
            .order("created_at")
            .execute()
        )

        contents = [
            types.Content(role=msg["role"], parts=[types.Part.from_text(text=msg["content"])])
            for msg in history_res.data
        ]
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=req.message)]))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        reply_text = response.text

        supabase.table("chat_history").insert(
            [
                {
                    "session_id": req.session_id,
                    "user_id": user["user_id"],
                    "role": "user",
                    "content": req.message,
                },
                {
                    "session_id": req.session_id,
                    "user_id": user["user_id"],
                    "role": "model",
                    "content": reply_text,
                },
            ]
        ).execute()

        return {"response": reply_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
