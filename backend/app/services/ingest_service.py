import io
import logging
import uuid
from pathlib import Path

import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from qdrant_client.models import PointStruct

from app.config import settings
from app.db.vector_store import ensure_collection_exists, get_qdrant_client
from app.services.rag_service import get_embedding_model

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_BYTES = 10 * 1024 * 1024


def extract_text_from_bytes(filename: str, data: bytes) -> list[dict]:
    """Pull page/section text from an uploaded file."""
    ext = Path(filename).suffix.lower()
    sections: list[dict] = []

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                sections.append({"text": text, "page_number": page_num})
        return sections

    if ext == ".docx":
        document = docx.Document(io.BytesIO(data))
        text_content = "\n".join(p.text for p in document.paragraphs if p.text.strip())
        if text_content.strip():
            sections.append({"text": text_content, "page_number": 1})
        return sections

    if ext in {".txt", ".md"}:
        text_content = data.decode("utf-8", errors="ignore")
        if text_content.strip():
            sections.append({"text": text_content, "page_number": 1})
        return sections

    raise ValueError(f"Unsupported file type: {ext or 'unknown'}")


def ingest_bytes(filename: str, data: bytes, user_id: str, thread_id: str) -> dict:
    """Chunk, embed, and upsert an uploaded document for this user."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Upload a PDF, Word (.docx), TXT, or Markdown file.")
    if not data:
        raise ValueError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError("File is larger than 10 MB.")

    sections = extract_text_from_bytes(filename, data)
    if not sections:
        raise ValueError(
            "Could not extract text. Try a text PDF, Word document, or TXT file."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
    )
    chunks: list[dict] = []
    chunk_idx = 0
    for section in sections:
        for split in splitter.split_text(section["text"]):
            if not split.strip():
                continue
            chunks.append(
                {
                    "text": split,
                    "source_filename": filename,
                    "page_number": section["page_number"],
                    "chunk_index": chunk_idx,
                    "user_id": user_id,
                    "thread_id": thread_id,
                }
            )
            chunk_idx += 1

    if not chunks:
        raise ValueError("No text chunks were created from this file.")

    ensure_collection_exists()
    client = get_qdrant_client()
    if client is None:
        raise RuntimeError(
            "The document store is unavailable. Restart the backend and try again."
        )

    logger.info("Embedding %s chunks from %s", len(chunks), filename)
    vectors = list(get_embedding_model().embed([c["text"] for c in chunks]))
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding failed for this document.")

    points = []
    for chunk, vector in zip(chunks, vectors):
        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{user_id}_{thread_id}_{chunk['source_filename']}_chunk_{chunk['chunk_index']}",
            )
        )
        points.append(
            PointStruct(id=point_id, vector=list(vector), payload=chunk)
        )

    batch_size = 100
    for i in range(0, len(points), batch_size):
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=points[i : i + batch_size],
        )

    logger.info("Indexed %s (%s chunks) for user %s", filename, len(chunks), user_id)
    return {
        "filename": filename,
        "chunks": len(chunks),
        "pages": len(sections),
    }
