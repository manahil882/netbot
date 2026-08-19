from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.gemini import client
from app.services.supabase import supabase
from google.genai import types

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/explain")
async def upload_and_explain(file: UploadFile = File(...), prompt: str = Form("Explain this document in detail.")):
    try:
        file_bytes = await file.read()
        
        # 1. Upload file object to Supabase bucket
        file_path = f"user_uploads/{file.filename}"
        supabase.storage.from_("documents").upload(file_path, file_bytes, {"content-type": file.content_type})
        
        # 2. Pass bytes directly to Gemini Multimodal engine
        part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=file.content_type or "application/pdf"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[part, prompt]
        )
        
        return {
            "filename": file.filename,
            "explanation": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))