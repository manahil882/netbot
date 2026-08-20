import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import supabase_client
from app.dependencies.auth import get_current_user_id
from app.models.chat import ChatRequest, ChatResponse
from app.services.agent_service import generate_chat_reply

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse, include_in_schema=False)
def chat_with_agent(
    payload: ChatRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> ChatResponse:
    logger.info("Chat request from %s: %s", user_id, payload.message[:80])
    try:
        thread_id = payload.thread_id

        if thread_id is None:
            title = payload.thread_title or payload.message[:48] or "New chat"
            thread = supabase_client.create_thread(str(user_id), title)
            thread_id = UUID(thread["id"])
        else:
            thread = supabase_client.get_thread_by_id(str(thread_id))
            if not thread:
                raise HTTPException(status_code=404, detail="Thread not found")
            if UUID(thread["user_id"]) != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

        history = supabase_client.get_thread_messages(str(thread_id))
        supabase_client.add_message(str(thread_id), "user", payload.message)

        answer, citations, tools_used = generate_chat_reply(
            payload.message, history, user_id=str(user_id), thread_id=str(thread_id)
        )
        supabase_client.add_message(str(thread_id), "assistant", answer)

        seen: set[tuple[str, int, int]] = set()
        unique_citations = []
        for cite in citations:
            key = (cite.source_filename, cite.page_number, cite.chunk_index)
            if key in seen:
                continue
            seen.add(key)
            unique_citations.append(cite)

        return ChatResponse(
            thread_id=thread_id,
            answer=answer,
            citations=unique_citations,
            tools_used=tools_used,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {exc}",
        ) from exc
