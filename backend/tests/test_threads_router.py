from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)

def test_create_thread_success() -> None:
    """Verifies that POST /threads creates a thread with the authenticated user ID."""
    mock_db_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "API Test Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z"
    }
    
    with patch("app.routers.threads.supabase_client.create_thread", return_value=mock_db_thread):
        response = client.post("/threads", json={"title": "API Test Thread"})
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "11111111-1111-1111-1111-111111111111"
        assert data["title"] == "API Test Thread"
        assert data["user_id"] == "00000000-0000-0000-0000-000000000000"

def test_list_threads_success() -> None:
    """Verifies that GET /threads lists threads for the authenticated user and maps updated_at to last_updated."""
    mock_db_threads = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000000",
            "title": "Thread One",
            "created_at": "2026-08-19T10:00:00Z",
            "updated_at": "2026-08-19T11:30:00Z"
        }
    ]
    
    with patch("app.routers.threads.supabase_client.list_threads", return_value=mock_db_threads):
        response = client.get("/threads")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "11111111-1111-1111-1111-111111111111"
        assert data[0]["title"] == "Thread One"
        # Verify renaming alias worked
        assert data[0]["last_updated"] == "2026-08-19T11:30:00Z"

def test_get_thread_history_access_denied() -> None:
    """Verifies that GET /threads/{thread_id} returns 403 if the thread belongs to a different user."""
    mock_other_user_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "99999999-9999-9999-9999-999999999999",  # Different owner
        "title": "Secret Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z"
    }
    
    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=mock_other_user_thread):
        response = client.get("/threads/11111111-1111-1111-1111-111111111111")
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied: thread does not belong to you"

def test_get_thread_history_not_found() -> None:
    """Verifies that GET /threads/{thread_id} returns 404 if the thread does not exist."""
    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=None):
        response = client.get("/threads/11111111-1111-1111-1111-111111111111")
        assert response.status_code == 404
        assert response.json()["detail"] == "Thread not found"

def test_get_thread_history_success() -> None:
    """Verifies that GET /threads/{thread_id} returns message list if thread ownership is valid."""
    mock_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "My Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z"
    }
    
    mock_messages = [
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "thread_id": "11111111-1111-1111-1111-111111111111",
            "role": "user",
            "content": "Hello",
            "created_at": "2026-08-19T10:01:00Z"
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "thread_id": "11111111-1111-1111-1111-111111111111",
            "role": "assistant",
            "content": "Hi there!",
            "created_at": "2026-08-19T10:02:00Z"
        }
    ]
    
    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=mock_thread), \
         patch("app.routers.threads.supabase_client.get_thread_messages", return_value=mock_messages):
        response = client.get("/threads/11111111-1111-1111-1111-111111111111")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Hello"
        assert data[1]["role"] == "assistant"
        assert data[1]["content"] == "Hi there!"

def test_post_message_success() -> None:
    """Verifies that POST /threads/{thread_id}/messages appends message and returns message data."""
    mock_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "My Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z"
    }
    
    mock_msg_inserted = {
        "id": "22222222-2222-2222-2222-222222222222",
        "thread_id": "11111111-1111-1111-1111-111111111111",
        "role": "user",
        "content": "A new query",
        "created_at": "2026-08-19T10:05:00Z"
    }
    
    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=mock_thread), \
         patch("app.routers.threads.supabase_client.add_message", return_value=mock_msg_inserted):
        response = client.post(
            "/threads/11111111-1111-1111-1111-111111111111/messages",
            json={"role": "user", "content": "A new query"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "22222222-2222-2222-2222-222222222222"
        assert data["content"] == "A new query"
        assert data["role"] == "user"
