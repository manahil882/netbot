from unittest.mock import MagicMock, patch
import pytest
from app.services.rag_service import retrieve_context

def test_retrieve_context_success() -> None:
    """Verifies retrieve_context embeds queries, queries Qdrant, and filters by score."""
    # Mock embedding model
    mock_model = MagicMock()
    mock_model.embed.return_value = [[0.1] * 384]
    
    # Mock Qdrant hits
    mock_hit_high = MagicMock()
    mock_hit_high.score = 0.85
    mock_hit_high.payload = {
        "text": "This chunk is relevant.",
        "source_filename": "doc1.pdf",
        "page_number": 3,
        "chunk_index": 5,
        "thread_id": "thread-1",
        "user_id": "user-1",
    }
    
    mock_hit_low = MagicMock()
    mock_hit_low.score = 0.10  # Below the default 0.25 threshold
    mock_hit_low.payload = {
        "text": "This chunk is irrelevant.",
        "source_filename": "doc2.pdf",
        "page_number": 1,
        "chunk_index": 0
    }
    
    mock_qdrant = MagicMock()
    mock_qdrant.query_points.return_value = MagicMock(points=[mock_hit_high, mock_hit_low])
    
    with patch("app.services.rag_service.get_embedding_model", return_value=mock_model), \
         patch("app.services.rag_service.qdrant_client", mock_qdrant):
        
        # Test default threshold (0.25)
        results = retrieve_context("test query", top_k=2, user_id="user-1", thread_id="thread-1")
        
        assert len(results) == 1
        assert results[0]["text"] == "This chunk is relevant."
        assert results[0]["source_filename"] == "doc1.pdf"
        assert results[0]["page_number"] == 3
        assert results[0]["chunk_index"] == 5
        assert results[0]["score"] == 0.85
        
        mock_model.embed.assert_called_once_with(["test query"])
        mock_qdrant.query_points.assert_called_once()
