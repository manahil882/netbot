import os
import sys
import uuid
import logging
from pathlib import Path
from pypdf import PdfReader
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastembed import TextEmbedding
from qdrant_client.models import PointStruct

# Setup PYTHONPATH so app modules can be imported
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from app.config import settings
from app.db.vector_store import qdrant_client, ensure_collection_exists

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def extract_text_from_file(file_path: Path) -> list[dict]:
    """Extracts text sections and maps them to a page/section number based on file type.

    Returns:
        list[dict]: List of dictionaries containing:
            - "text": The extracted text.
            - "page_number": Page or section index (1-indexed).
    """
    ext = file_path.suffix.lower()
    sections = []

    try:
        if ext == ".pdf":
            # PDF Reader
            reader = PdfReader(file_path)
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    sections.append({"text": text, "page_number": page_num})
        
        elif ext == ".docx":
            # Word Document Reader
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            
            # Since Word docs don't have distinct page markers in python-docx,
            # we group paragraphs or treat the whole text as page 1.
            text_content = "\n".join(full_text)
            if text_content.strip():
                sections.append({"text": text_content, "page_number": 1})

        elif ext in (".txt", ".md"):
            # Plain Text and Markdown Reader
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
            if text_content.strip():
                sections.append({"text": text_content, "page_number": 1})

        else:
            logger.warning(f"Unsupported file format: {ext} for file {file_path.name}")

    except Exception as e:
        logger.error(f"Failed to read file {file_path.name} ({ext}): {e}")

    return sections

def ingest_pdfs(raw_data_dir: Path) -> None:
    """Reads all supported documents (PDF, DOCX, TXT, MD), chunks them, embeds them, and upserts them to Qdrant."""
    ensure_collection_exists()

    # Look for all supported extensions
    supported_extensions = ("*.pdf", "*.docx", "*.txt", "*.md")
    document_files = []
    for ext in supported_extensions:
        document_files.extend(list(raw_data_dir.glob(ext)))

    if not document_files:
        logger.info(f"No supported document files found in {raw_data_dir}")
        return

    # Text splitter config
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len
    )

    all_chunks = []
    files_processed = 0

    for doc_path in document_files:
        filename = doc_path.name
        logger.info(f"Processing file: {filename}")
        
        sections = extract_text_from_file(doc_path)
        if not sections:
            continue
            
        chunk_idx = 0
        for section in sections:
            splits = splitter.split_text(section["text"])
            for split in splits:
                if not split.strip():
                    continue
                all_chunks.append({
                    "text": split,
                    "source_filename": filename,
                    "page_number": section["page_number"],
                    "chunk_index": chunk_idx
                })
                chunk_idx += 1
        
        files_processed += 1

    if not all_chunks:
        logger.info("No chunks were created. Ingestion complete.")
        return

    logger.info(f"Generated {len(all_chunks)} chunks from {files_processed} files. Embedding chunks...")

    # Embed using fastembed BAAI/bge-small-en-v1.5
    try:
        embedding_model = TextEmbedding()
        texts = [chunk["text"] for chunk in all_chunks]
        vectors = list(embedding_model.embed(texts))
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return

    logger.info(f"Generated {len(vectors)} embeddings. Upserting into Qdrant...")

    points = []
    for idx, (chunk, vector) in enumerate(zip(all_chunks, vectors)):
        # Generate deterministic UUID for re-runnability
        unique_str = f"{chunk['source_filename']}_chunk_{chunk['chunk_index']}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_str))
        
        points.append(PointStruct(
            id=point_id,
            vector=list(vector),
            payload=chunk
        ))

    try:
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            qdrant_client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=batch
            )
        logger.info("--- Ingestion Summary ---")
        logger.info(f"Files processed: {files_processed}")
        logger.info(f"Chunks created: {len(all_chunks)}")
        logger.info(f"Chunks upserted: {len(points)}")
    except Exception as e:
        logger.error(f"Failed to upsert points into Qdrant: {e}")

if __name__ == "__main__":
    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    ingest_pdfs(raw_dir)
