import io
import os
import tempfile
import uuid

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
import whisper
from gtts import gTTS

from app.dependencies import get_current_user

router = APIRouter(prefix="/audio", tags=["Audio"])

# Loaded once, lazily, on first request rather than at import time -- avoids
# a slow model download/load blocking app startup or every reload.
_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        # "base" balances speed/accuracy; bump to "small"/"medium" if
        # transcription quality on accents/background noise isn't good enough.
        _whisper_model = whisper.load_model("base")
    return _whisper_model


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Speech-to-text. Accepts common audio formats (mp3, wav, m4a, webm...) --
    whisper shells out to ffmpeg for decoding, so ffmpeg must be installed on
    the host (not a pip package; apt/brew install it separately)."""
    suffix = os.path.splitext(file.filename or "")[1] or ".wav"
    contents = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        model = _get_whisper_model()
        result = model.transcribe(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    finally:
        os.remove(tmp_path)

    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language"),
    }


@router.post("/speak")
async def synthesize_speech(
    text: str = Form(...),
    lang: str = Form("en"),
    user=Depends(get_current_user),
):
    """Text-to-speech. Returns an MP3 audio stream."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    try:
        tts = gTTS(text=text, lang=lang)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {e}")

    filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"
    return StreamingResponse(
        buffer,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
