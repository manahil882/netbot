import logging
from datetime import datetime, timezone
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def check_supabase_connection() -> bool:
    """Verifies connection to Supabase by querying the users table."""
    try:
        supabase.table("users").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        raise e


def create_user(name: str, email: str, hashed_password: str, face_embedding: list | None = None) -> dict:
    payload: dict = {
        "name": name,
        "email": email,
        "hashed_password": hashed_password,
    }
    if face_embedding is not None:
        payload["face_embedding"] = face_embedding
    response = supabase.table("users").insert(payload).execute()
    if not response.data:
        raise ValueError("Failed to create user")
    return response.data[0]


def get_user_by_email(email: str) -> dict | None:
    try:
        response = (
            supabase.table("users")
            .select("id, name, email, hashed_password, face_embedding")
            .eq("email", email)
            .single()
            .execute()
        )
        return response.data
    except Exception:
        return None


def get_user_by_id(user_id: str) -> dict | None:
    try:
        response = (
            supabase.table("users")
            .select("id, name, email, hashed_password, face_embedding")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return response.data
    except Exception:
        return None


def update_user_face_embedding(user_id: str, face_embedding: list) -> dict:
    response = (
        supabase.table("users")
        .update({"face_embedding": face_embedding})
        .eq("id", user_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Failed to update face embedding")
    return response.data[0]


def create_thread(user_id: str, title: str) -> dict:
    """Creates a new conversation thread for a user.

    Args:
        user_id: The UUID of the owner user.
        title: The display title of the thread.

    Returns:
        dict: The created thread record.
    """
    try:
        response = supabase.table("threads").insert({
            "user_id": user_id,
            "title": title
        }).execute()
        if not response.data:
            raise ValueError("Failed to create thread: no data returned")
        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating thread for user {user_id}: {e}")
        raise e

def list_threads(user_id: str) -> list[dict]:
    """Lists all conversation threads for a user, ordered by updated_at descending.

    Args:
        user_id: The UUID of the owner user.

    Returns:
        list[dict]: List of thread records.
    """
    try:
        response = supabase.table("threads")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"Error listing threads for user {user_id}: {e}")
        raise e

def get_thread_by_id(thread_id: str) -> dict | None:
    """Retrieves a single thread by its ID.

    Args:
        thread_id: The UUID of the thread.

    Returns:
        dict | None: The thread record if found, else None.
    """
    try:
        response = supabase.table("threads")\
            .select("*")\
            .eq("id", thread_id)\
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching thread {thread_id}: {e}")
        raise e

def get_thread_messages(thread_id: str) -> list[dict]:
    """Fetches all messages in a thread, ordered by created_at ascending.

    Args:
        thread_id: The UUID of the thread.

    Returns:
        list[dict]: List of message records.
    """
    try:
        response = supabase.table("messages")\
            .select("*")\
            .eq("thread_id", thread_id)\
            .order("created_at", desc=False)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting messages for thread {thread_id}: {e}")
        raise e

def add_message(thread_id: str, role: str, content: str) -> dict:
    """Appends a message to a thread and updates the thread's updated_at timestamp.

    Args:
        thread_id: The UUID of the thread.
        role: The sender role ('user' or 'assistant').
        content: The message text content.

    Returns:
        dict: The created message record.
    """
    try:
        # Insert message
        msg_response = supabase.table("messages").insert({
            "thread_id": thread_id,
            "role": role,
            "content": content
        }).execute()
        if not msg_response.data:
            raise ValueError("Failed to append message: no data returned")
        
        # Update thread's updated_at timestamp
        supabase.table("threads").update({
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", thread_id).execute()

        return msg_response.data[0]
    except Exception as e:
        logger.error(f"Error adding message to thread {thread_id}: {e}")
        raise e
