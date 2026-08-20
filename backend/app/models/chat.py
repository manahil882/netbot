from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_filename: str
    page_number: int = 0
    chunk_index: int = 0
    score: float = 0.0
    excerpt: str = ""


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: UUID | None = None
    thread_title: str | None = None


class ChatResponse(BaseModel):
    thread_id: UUID
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
