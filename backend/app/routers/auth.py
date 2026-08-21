import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from app.db import supabase_client
from app.dependencies.auth import get_current_user_id
from app.models.user import TokenResponse
from app.services.auth_service import (
    create_access_token,
    create_email_verified_token,
    hash_password,
    require_email_verified_token,
    verify_password,
)
from app.services.email_service import send_verification_email
from app.services.face_service import cosine_similarity, face_embedding_from_bytes, stored_embedding
from app.services.otp_service import generate_otp_code, save_otp, verify_otp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _has_face(user: dict) -> bool:
    return stored_embedding(user.get("face_embedding")) is not None


def _token_for(user: dict) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(UUID(user["id"]), user["email"]),
        user_id=UUID(user["id"]),
        name=user["name"],
        email=user["email"],
        face_enrolled=_has_face(user),
    )


@router.get("/check-email")
def check_email(email: str) -> dict:
    """Return whether an email can be used for a new account."""
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    taken = supabase_client.get_user_by_email(normalized) is not None
    return {"available": not taken, "email": normalized}


@router.post("/send-code")
async def send_verification_code(email: str = Form(...)) -> dict:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if supabase_client.get_user_by_email(normalized):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this email. Please sign in instead.",
        )

    code = generate_otp_code()
    save_otp(normalized, code)
    try:
        await send_verification_email(normalized, code)
    except Exception as exc:
        logger.exception("Failed to send verification email")
        raise HTTPException(
            status_code=503,
            detail="Could not send verification email. Try again shortly.",
        ) from exc

    payload: dict = {
        "ok": True,
        "email": normalized,
        "expires_in_minutes": settings.EMAIL_OTP_EXPIRE_MINUTES,
    }
    if settings.EMAIL_DEV_EXPOSE_CODE or not settings.RESEND_API_KEY:
        # Local/dev convenience when Resend is not configured.
        payload["dev_code"] = code
    return payload


@router.post("/verify-code")
def verify_verification_code(email: str = Form(...), code: str = Form(...)) -> dict:
    normalized = email.strip().lower()
    if not verify_otp(normalized, code):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    token = create_email_verified_token(normalized)
    return {"ok": True, "email": normalized, "email_token": token}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    email_token: str = Form(...),
    face_image: UploadFile | None = File(None),
) -> TokenResponse:
    normalized_email = email.strip().lower()
    try:
        require_email_verified_token(email_token, normalized_email)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Verify your email with the code we sent before creating an account.",
        ) from exc

    if supabase_client.get_user_by_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this email. Please sign in instead.",
        )

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
            name=name.strip(),
            email=normalized_email,
            hashed_password=hash_password(password),
            face_embedding=face_embedding,
        )
    except Exception as exc:
        logger.exception("Failed to create user")
        message = str(exc).lower()
        if "duplicate" in message or "unique" in message or "already exists" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already exists for this email. Please sign in instead.",
            ) from exc
        raise HTTPException(status_code=500, detail="Could not create account. Try again.") from exc
    return _token_for(user)


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = supabase_client.get_user_by_email(form.username.strip().lower())
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_for(user)


@router.post("/face-login", response_model=TokenResponse)
async def face_login(
    email: str = Form(...),
    face_image: UploadFile = File(...),
) -> TokenResponse:
    user = supabase_client.get_user_by_email(email.strip().lower())
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

    return _token_for(user)


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
    return {"status": "enrolled", "face_enrolled": True}


@router.patch("/me")
async def update_me(
    name: str = Form(...),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    cleaned = name.strip()
    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="Enter a valid display name")
    user = supabase_client.update_user_name(str(user_id), cleaned)
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "face_enrolled": _has_face(user),
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user_id: UUID = Depends(get_current_user_id)) -> None:
    from app.services.rag_service import delete_user_vectors

    try:
        delete_user_vectors(str(user_id))
    except Exception:
        logger.exception("Could not delete vector data for user %s", user_id)

    try:
        supabase_client.delete_user(str(user_id))
    except Exception as exc:
        logger.exception("Failed to delete user %s", user_id)
        raise HTTPException(status_code=500, detail="Could not delete account") from exc
