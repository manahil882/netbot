from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from deepface import DeepFace
import numpy as np
import cv2
import json

from app.services.supabase import supabase
from app.services.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

FACE_MATCH_THRESHOLD = 0.70  # cosine similarity; tune against real enrollment data


def _face_embedding_from_upload(contents: bytes) -> list:
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode face image")

    result = DeepFace.represent(img_path=img, model_name="Facenet")
    return result[0]["embedding"]


def _fetch_profile_by_email(email: str):
    """single() raises if no row matches on some postgrest-py versions,
    returns empty data on others -- normalize both to None."""
    try:
        res = (
            supabase.table("profiles")
            .select("id, email, password_hash, face_embedding")
            .eq("email", email)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


@router.post("/signup")
async def signup(
    email: str = Form(...),
    password: str = Form(...),
    face_image: UploadFile = File(...),
):
    if _fetch_profile_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")

    contents = await face_image.read()
    embedding = _face_embedding_from_upload(contents)
    password_hash = hash_password(password)

    insert_res = (
        supabase.table("profiles")
        .insert(
            {
                "email": email,
                "password_hash": password_hash,
                "face_embedding": json.dumps(embedding),
            }
        )
        .execute()
    )

    if not insert_res.data:
        raise HTTPException(status_code=500, detail="Failed to create profile")

    user = insert_res.data[0]
    token = create_access_token(user_id=user["id"], email=email)

    return {
        "message": "User registered successfully",
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
    }


@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    profile = _fetch_profile_by_email(email)
    if not profile or not verify_password(password, profile["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user_id=profile["id"], email=profile["email"])
    return {"access_token": token, "token_type": "bearer", "user_id": profile["id"]}


@router.post("/face-login")
async def face_login(email: str = Form(...), face_image: UploadFile = File(...)):
    profile = _fetch_profile_by_email(email)
    if not profile or not profile.get("face_embedding"):
        raise HTTPException(status_code=404, detail="No face profile found for this email")

    stored_embedding = np.array(json.loads(profile["face_embedding"]))

    contents = await face_image.read()
    live_embedding = np.array(_face_embedding_from_upload(contents))

    similarity = float(
        np.dot(stored_embedding, live_embedding)
        / (np.linalg.norm(stored_embedding) * np.linalg.norm(live_embedding))
    )

    if similarity < FACE_MATCH_THRESHOLD:
        raise HTTPException(status_code=401, detail="Facial recognition verification failed")

    token = create_access_token(user_id=profile["id"], email=profile["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": profile["id"],
        "similarity": similarity,
    }
