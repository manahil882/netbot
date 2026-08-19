import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.thread import ThreadCreateRequest, ThreadOut, ThreadSummary, MessageCreate, MessageOut
from app.db import supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/threads", tags=["threads"])

def get_current_user_id() -> UUID:
    """Dependency that returns the authenticated user's ID.

    TODO(teammate): Replace this mock dependency with the real authentication dependency
    (e.g., JWT decoding and validation) once auth is wired up.
    """
    # Using a fixed default UUID for now (all endpoints require it)
    return UUID("00000000-0000-0000-0000-000000000000")

@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
async def create_new_thread(
    payload: ThreadCreateRequest,
    user_id: UUID = Depends(get_current_user_id)
) -> ThreadOut:
    """Creates a new conversation thread for the authenticated user."""
    try:
        thread_data = supabase_client.create_thread(str(user_id), payload.title)
        return ThreadOut.model_validate(thread_data)
    except Exception as e:
        logger.error(f"Failed to create thread: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.get("", response_model=list[ThreadSummary])
async def get_user_threads(
    user_id: UUID = Depends(get_current_user_id)
) -> list[ThreadSummary]:
    """Lists all threads belonging to the authenticated user, ordered by last updated."""
    try:
        threads_data = supabase_client.list_threads(str(user_id))
        return [ThreadSummary.model_validate(t) for t in threads_data]
    except Exception as e:
        logger.error(f"Failed to list threads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.get("/{thread_id}", response_model=list[MessageOut])
async def get_thread_history(
    thread_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
) -> list[MessageOut]:
    """Fetches the complete message history for a specific thread.

    Validates that the thread exists and belongs to the authenticated user.
    """
    try:
        thread = supabase_client.get_thread_by_id(str(thread_id))
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )
        
        # Verify ownership
        if UUID(thread["user_id"]) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: thread does not belong to you"
            )

        messages = supabase_client.get_thread_messages(str(thread_id))
        return [MessageOut.model_validate(m) for m in messages]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread history for {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/{thread_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def post_message_to_thread(
    thread_id: UUID,
    payload: MessageCreate,
    user_id: UUID = Depends(get_current_user_id)
) -> MessageOut:
    """Appends a new message to the thread history.

    Validates that the thread exists and belongs to the authenticated user.
    This endpoint is used internally by the /chat endpoint once a teammate builds it.
    """
    try:
        thread = supabase_client.get_thread_by_id(str(thread_id))
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )
        
        # Verify ownership
        if UUID(thread["user_id"]) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: thread does not belong to you"
            )

        msg_data = supabase_client.add_message(str(thread_id), payload.role, payload.content)
        return MessageOut.model_validate(msg_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to append message to thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
