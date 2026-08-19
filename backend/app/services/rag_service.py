import logging
from fastembed import TextEmbedding
from app.db.vector_store import qdrant_client
from app.config import settings

logger = logging.getLogger(__name__)

# Lazily instantiated embedding model singleton
_embedding_model: TextEmbedding | None = None

def get_embedding_model() -> TextEmbedding:
    """Returns the singleton instance of the FastEmbed TextEmbedding model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing FastEmbed TextEmbedding model...")
        _embedding_model = TextEmbedding()
    return _embedding_model

def retrieve_context(query: str, top_k: int = 5, min_score: float = 0.4) -> list[dict]:
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
    try:
        model = get_embedding_model()
        # Embed the single query string
        query_vectors = list(model.embed([query]))
        if not query_vectors:
            logger.warning("No embedding vector generated for query.")
            return []
        query_vector = list(query_vectors[0])

        # Search the Qdrant collection
        search_results = qdrant_client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )

        results = []
        for hit in search_results:
            if hit.score >= min_score:
                payload = hit.payload or {}
                results.append({
                    "text": payload.get("text", ""),
                    "source_filename": payload.get("source_filename", ""),
                    "page_number": payload.get("page_number", 0),
                    "chunk_index": payload.get("chunk_index", 0),
                    "score": hit.score
                })
        return results
    except Exception as e:
        logger.error(f"Failed to retrieve context for query '{query}': {e}")
        # Return empty list on failure rather than crashing the chat pipeline
        return []
