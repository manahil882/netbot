import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from app.db import supabase_client
from app.dependencies.auth import get_current_user_id
from app.models.user import TokenResponse
from app.services.auth_service import create_access_token, hash_password, verify_password
from app.services.face_service import cosine_similarity, face_embedding_from_bytes, stored_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    face_image: UploadFile | None = File(None),
) -> TokenResponse:
    if supabase_client.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")

    face_embedding = None
    if face_image is not None:
        try:
            contents = await face_image.read()
            face_embedding = face_embedding_from_bytes(contents)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Face enrollment failed during register")
            raise HTTPException(
                status_code=503,
                detail="Face recognition is unavailable. Install ML deps: pip install -r requirements-ml.txt",
            ) from exc

    try:
        user = supabase_client.create_user(
            name=name,
            email=email,
            hashed_password=hash_password(password),
            face_embedding=face_embedding,
        )
    except Exception as exc:
        logger.exception("Failed to create user")
        raise HTTPException(status_code=500, detail="Could not create account. Try again.") from exc
    token = create_access_token(UUID(user["id"]), user["email"])
    return TokenResponse(
        access_token=token,
        user_id=UUID(user["id"]),
        name=user["name"],
        email=user["email"],
    )


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = supabase_client.get_user_by_email(form.username)
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(UUID(user["id"]), user["email"])
    return TokenResponse(
        access_token=token,
        user_id=UUID(user["id"]),
        name=user["name"],
        email=user["email"],
    )


@router.post("/face-login", response_model=TokenResponse)
async def face_login(
    email: str = Form(...),
    face_image: UploadFile = File(...),
) -> TokenResponse:
    user = supabase_client.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found for this email")

    stored = stored_embedding(user.get("face_embedding"))
    if not stored:
        raise HTTPException(status_code=400, detail="Face ID not enrolled for this account")

    contents = await face_image.read()
    probe = face_embedding_from_bytes(contents)
    score = cosine_similarity(stored, probe)
    if score < settings.FACE_MATCH_THRESHOLD:
        raise HTTPException(status_code=401, detail="Face did not match")

    token = create_access_token(UUID(user["id"]), user["email"])
    return TokenResponse(
        access_token=token,
        user_id=UUID(user["id"]),
        name=user["name"],
        email=user["email"],
    )


@router.post("/face-enroll")
async def face_enroll(
    face_image: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user = supabase_client.get_user_by_id(str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    contents = await face_image.read()
    embedding = face_embedding_from_bytes(contents)
    supabase_client.update_user_face_embedding(str(user_id), embedding)
    return {"status": "enrolled"}
