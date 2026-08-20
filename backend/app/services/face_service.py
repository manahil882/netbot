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
        result = DeepFace.represent(img_path=img, model_name="Facenet", enforce_detection=False)
        return result[0]["embedding"]
    except Exception as exc:
        logger.error("Face embedding failed: %s", exc)
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
