from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.supabase import supabase
from deepface import DeepFace
import numpy as np
import cv2
import json

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/signup")
async def signup(email: str = Form(...), password: str = Form(...), face_image: UploadFile = File(...)):
    # Standard Auth Creation
    auth_res = supabase.auth.sign_up({"email": email, "password": password})
    if not auth_res.user:
        raise HTTPException(status_code=400, detail="Signup failed")
    
    # Process Facial Embedding
    contents = await face_image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    embedding = DeepFace.represent(img_path=img, model_name="Facenet")[0]["embedding"]
    
    # Store embedding array in database tied to profile
    supabase.table("profiles").insert({
        "id": auth_res.user.id,
        "email": email,
        "face_embedding": json.dumps(embedding)
    }).execute()
    
    return {"message": "User registered successfully", "user_id": auth_res.user.id}

@router.post("/face-login")
async def face_login(email: str = Form(...), face_image: UploadFile = File(...)):
    # Fetch registered embedding
    profile = supabase.table("profiles").select("id, face_embedding").eq("email", email).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    stored_embedding = json.loads(profile.data["face_embedding"])
    
    # Generate live input image embedding
    contents = await face_image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    live_embedding = DeepFace.represent(img_path=img, model_name="Facenet")[0]["embedding"]
    
    # Calculate cosine similarity distance
    distance = np.dot(stored_embedding, live_embedding) / (np.linalg.norm(stored_embedding) * np.linalg.norm(live_embedding))
    
    if distance > 0.70: # Cosine similarity threshold match
        return {"status": "authenticated", "user_id": profile.data["id"]}
    else:
        raise HTTPException(status_code=401, detail="Facial recognition verification failed")