import logging
from fastembed import TextEmbedding
from app.db.vector_store import get_qdrant_client, qdrant_client
from app.config import settings
from qdrant_client.models import FieldCondition, Filter, MatchValue

logger = logging.getLogger(__name__)

# Lazily instantiated embedding model singleton
_embedding_model: TextEmbedding | None = None


def _owner_filter(user_id: str | None, thread_id: str | None = None) -> Filter | None:
    must: list[FieldCondition] = []
    if user_id:
        must.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
    if thread_id:
        must.append(FieldCondition(key="thread_id", match=MatchValue(value=thread_id)))
    if not must:
        return None
    return Filter(must=must)


def _payload_chunk(payload: dict, score: float = 1.0) -> dict:
    return {
        "text": payload.get("text", ""),
        "source_filename": payload.get("source_filename", ""),
        "page_number": payload.get("page_number", 0),
        "chunk_index": payload.get("chunk_index", 0),
        "score": score,
        "thread_id": payload.get("thread_id", ""),
    }


def _same_thread(payload: dict | None, thread_id: str | None) -> bool:
    if not thread_id:
        return False
    return str((payload or {}).get("thread_id") or "") == str(thread_id)

def get_embedding_model() -> TextEmbedding:
    """Returns the singleton instance of the FastEmbed TextEmbedding model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing FastEmbed TextEmbedding model...")
        _embedding_model = TextEmbedding()
    return _embedding_model

def retrieve_context(
    query: str,
    top_k: int = 8,
    min_score: float = 0.2,
    user_id: str | None = None,
    thread_id: str | None = None,
) -> list[dict]:
    """Retrieves top-k relevant document chunks from Qdrant matching the query.

    Example Usage:
        from app.services.rag_service import retrieve_context
        chunks = retrieve_context("What is the refund policy?", top_k=3)
        for chunk in chunks:
            print(f"Content: {chunk['text']}")
            print(f"Source: {chunk['source_filename']} (Page {chunk['page_number']})")

    Args:
        query: The user query string.
        top_k: The maximum number of chunks to retrieve. Defaults to 5.
        min_score: The minimum similarity score threshold (0.0 to 1.0). Chunks with
                   scores below this threshold are ignored. Defaults to 0.4.

    Returns:
        list[dict]: A list of matched chunks, where each chunk is a dictionary containing:
            - "text": The textual content of the chunk.
            - "source_filename": The name of the originating PDF file.
            - "page_number": The page number in the original PDF (1-indexed).
            - "chunk_index": The index of the chunk in the document.
            - "score": The cosine similarity score of the match.
    """
    if not user_id or not thread_id:
        return []
    try:
        client = qdrant_client if qdrant_client is not None else get_qdrant_client()
        if client is None:
            logger.warning("Qdrant client is unavailable; returning no RAG context.")
            return []
        model = get_embedding_model()
        query_vectors = list(model.embed([query]))
        if not query_vectors:
            logger.warning("No embedding vector generated for query.")
            return []
        query_vector = list(query_vectors[0])

        query_filter = _owner_filter(user_id, thread_id)

        response = client.query_points(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query=query_vector,
            limit=max(top_k * 4, 12),
            query_filter=query_filter,
        )
        search_results = getattr(response, "points", response)

        results = []
        for hit in search_results:
            if not _same_thread(hit.payload, thread_id):
                continue
            if hit.score >= min_score:
                results.append(_payload_chunk(hit.payload or {}, float(hit.score)))
            if len(results) >= top_k:
                break
        if results:
            return results

        # query_points can ignore payload filters; rank this chat's chunks only.
        thread_chunks = list_thread_chunks(user_id, thread_id)
        return _keyword_rank(query, thread_chunks, top_k)
    except Exception as e:
        logger.error(f"Failed to retrieve context for query '{query}': {e}")
        return []


def _keyword_rank(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    words = [w for w in query.lower().split() if len(w) > 2]
    if not words or not chunks:
        return []
    ranked: list[tuple[int, dict]] = []
    for chunk in chunks:
        text = (chunk.get("text") or "").lower()
        score = sum(1 for word in words if word in text)
        if score:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in ranked[:top_k]]


def list_thread_chunks(user_id: str, thread_id: str, limit: int = 400) -> list[dict]:
    """Return indexed chunks for a chat, in document order."""
    client = qdrant_client if qdrant_client is not None else get_qdrant_client()
    if client is None:
        return []
    try:
        chunks: list[dict] = []
        offset = None
        page_size = min(100, limit)
        while len(chunks) < limit:
            points, offset = client.scroll(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                scroll_filter=_owner_filter(user_id, thread_id),
                limit=min(page_size, limit - len(chunks)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            chunks.extend(
                _payload_chunk(p.payload or {}, 1.0)
                for p in points
                if _same_thread(p.payload, thread_id)
            )
            if offset is None or not points:
                break
        chunks.sort(key=lambda c: (c["source_filename"], int(c.get("chunk_index") or 0)))
        return chunks
    except Exception as exc:
        logger.error("Failed to list thread chunks: %s", exc)
        return []


def list_thread_documents(user_id: str, thread_id: str) -> list[dict]:
    chunks = list_thread_chunks(user_id, thread_id)
    by_name: dict[str, dict] = {}
    for chunk in chunks:
        name = chunk["source_filename"]
        entry = by_name.setdefault(name, {"filename": name, "chunks": 0, "pages": set()})
        entry["chunks"] += 1
        page = int(chunk.get("page_number") or 0)
        if page:
            entry["pages"].add(page)
    return [
        {
            "filename": item["filename"],
            "chunks": item["chunks"],
            "pages": len(item["pages"]) or 1,
        }
        for item in by_name.values()
    ]


def delete_thread_document(user_id: str, thread_id: str, filename: str) -> int:
    """Remove one uploaded file from a chat. Returns deleted point count estimate."""
    from qdrant_client.models import FilterSelector

    client = qdrant_client if qdrant_client is not None else get_qdrant_client()
    if client is None:
        raise RuntimeError("The document store is unavailable.")
    filt = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="thread_id", match=MatchValue(value=thread_id)),
            FieldCondition(key="source_filename", match=MatchValue(value=filename)),
        ]
    )
    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=FilterSelector(filter=filt),
    )
    return 1


def delete_thread_vectors(user_id: str, thread_id: str) -> None:
    """Remove every indexed chunk belonging to a chat."""
    from qdrant_client.models import FilterSelector

    client = qdrant_client if qdrant_client is not None else get_qdrant_client()
    if client is None:
        return
    filt = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="thread_id", match=MatchValue(value=thread_id)),
        ]
    )
    try:
        client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=FilterSelector(filter=filt),
        )
    except Exception as exc:
        logger.error("Failed to delete thread vectors: %s", exc)
