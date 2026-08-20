import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.dependencies.auth import get_current_user_id
from app.services.ingest_service import ingest_bytes
from app.services.rag_service import delete_thread_document, list_thread_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    thread_id: str = Form(...),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    filename = file.filename or "document.txt"
    data = file.file.read()
    try:
        UUID(thread_id)
        result = ingest_bytes(filename, data, str(user_id), thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Document ingest failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Document ingest failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not index this document. Try another file.",
        ) from exc
    return result


@router.get("")
def list_documents(
    thread_id: str = Query(...),
    user_id: UUID = Depends(get_current_user_id),
) -> list[dict]:
    return list_thread_documents(str(user_id), thread_id)


@router.delete("")
def remove_document(
    thread_id: str = Query(...),
    filename: str = Query(...),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    try:
        delete_thread_document(str(user_id), thread_id, filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "deleted", "filename": filename}
