from unittest.mock import patch
from uuid import UUID

from app.models.chat import Citation


def test_create_thread_success(client) -> None:
    mock_db_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "API Test Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z",
    }

    with patch("app.routers.threads.supabase_client.create_thread", return_value=mock_db_thread):
        response = client.post("/threads", json={"title": "API Test Thread"})
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "11111111-1111-1111-1111-111111111111"
        assert data["title"] == "API Test Thread"


def test_list_threads_success(client) -> None:
    mock_db_threads = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "00000000-0000-0000-0000-000000000000",
            "title": "Thread One",
            "created_at": "2026-08-19T10:00:00Z",
            "updated_at": "2026-08-19T11:30:00Z",
        }
    ]

    with patch("app.routers.threads.supabase_client.list_threads", return_value=mock_db_threads):
        response = client.get("/threads")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["last_updated"] == "2026-08-19T11:30:00Z"


def test_get_thread_history_access_denied(client) -> None:
    mock_other_user_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "99999999-9999-9999-9999-999999999999",
        "title": "Secret Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z",
    }

    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=mock_other_user_thread):
        response = client.get("/threads/11111111-1111-1111-1111-111111111111")
        assert response.status_code == 403


def test_get_thread_history_not_found(client) -> None:
    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=None):
        response = client.get("/threads/11111111-1111-1111-1111-111111111111")
        assert response.status_code == 404


def test_get_thread_history_success(client) -> None:
    mock_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "My Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z",
    }
    mock_messages = [
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "thread_id": "11111111-1111-1111-1111-111111111111",
            "role": "user",
            "content": "Hello",
            "created_at": "2026-08-19T10:01:00Z",
        }
    ]

    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=mock_thread), patch(
        "app.routers.threads.supabase_client.get_thread_messages", return_value=mock_messages
    ):
        response = client.get("/threads/11111111-1111-1111-1111-111111111111")
        assert response.status_code == 200
        assert response.json()[0]["content"] == "Hello"


def test_post_message_success(client) -> None:
    mock_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "My Thread",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z",
    }
    mock_msg_inserted = {
        "id": "22222222-2222-2222-2222-222222222222",
        "thread_id": "11111111-1111-1111-1111-111111111111",
        "role": "user",
        "content": "A new query",
        "created_at": "2026-08-19T10:05:00Z",
    }

    with patch("app.routers.threads.supabase_client.get_thread_by_id", return_value=mock_thread), patch(
        "app.routers.threads.supabase_client.add_message", return_value=mock_msg_inserted
    ):
        response = client.post(
            "/threads/11111111-1111-1111-1111-111111111111/messages",
            json={"role": "user", "content": "A new query"},
        )
        assert response.status_code == 201


def test_chat_endpoint_creates_thread(client) -> None:
    mock_thread = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "title": "Refund policy",
        "created_at": "2026-08-19T10:00:00Z",
        "updated_at": "2026-08-19T10:00:00Z",
    }

    with patch("app.routers.chat.supabase_client.create_thread", return_value=mock_thread), patch(
        "app.routers.chat.supabase_client.get_thread_messages", return_value=[]
    ), patch("app.routers.chat.supabase_client.add_message", return_value={}), patch(
        "app.routers.chat.generate_chat_reply",
        return_value=("Here is the answer.", [Citation(source_filename="policy.pdf")], ["search_documents"]),
    ):
        response = client.post("/chat", json={"message": "What is the refund policy?"})
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "11111111-1111-1111-1111-111111111111"
        assert "answer" in data
        assert data["tools_used"] == ["search_documents"]
