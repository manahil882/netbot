import json
import logging

import numpy as np
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _decode_image(contents: bytes):
    import cv2

    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode face image")
    return img


def face_embedding_from_bytes(contents: bytes) -> list:
    try:
        from deepface import DeepFace
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Face recognition dependencies are not installed on the server",
        ) from exc

    img = _decode_image(contents)
    try:
        # Skip Haar/RetinaFace detection: the UI already frames the face.
        # opencv-python-headless does not ship haarcascade XML files.
        result = DeepFace.represent(
            img_path=img,
            model_name="Facenet",
            detector_backend="skip",
            enforce_detection=False,
        )
        embedding = result[0]["embedding"]
        if not embedding:
            raise HTTPException(status_code=400, detail="Could not extract face from image")
        return embedding
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Face embedding failed: %s", exc)
        message = str(exc)
        if "downloading" in message.lower() or "facenet_weights" in message.lower():
            raise HTTPException(
                status_code=503,
                detail="Face model is still downloading. Wait a moment and tap Finish enrollment again.",
            ) from exc
        raise HTTPException(status_code=400, detail="Could not extract face from image") from exc


def cosine_similarity(a: list, b: list) -> float:
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def stored_embedding(raw: object) -> list | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    return list(raw)
