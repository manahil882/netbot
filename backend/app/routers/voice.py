import io
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from gtts import gTTS
from google import genai
from google.genai import types

from app.config import settings
from app.dependencies.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    _user_id=Depends(get_current_user_id),
) -> dict:
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    mime = file.content_type or "audio/webm"
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime),
            "Transcribe the spoken words exactly. Return only the transcript text.",
        ],
    )
    text = (response.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="No speech detected")
    return {"text": text}


@router.post("/speak")
async def speak_text(
    text: str = Form(...),
    _user_id=Depends(get_current_user_id),
) -> StreamingResponse:
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Text is required")

    buffer = io.BytesIO()
    gTTS(text=cleaned, lang="en").write_to_fp(buffer)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="audio/mpeg")
