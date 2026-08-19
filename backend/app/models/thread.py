from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict

class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    role: str = Field(..., description="Role of the sender. Must be 'user' or 'assistant'.")
    content: str = Field(..., description="Text content of the message.")

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ("user", "assistant"):
            raise ValueError("Role must be 'user' or 'assistant'")
        return value

class MessageOut(BaseModel):
    """Schema for message response."""
    id: UUID
    thread_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ThreadCreateRequest(BaseModel):
    """Schema for the thread creation request body."""
    title: str = Field(..., description="Title of the thread.")

class ThreadCreate(BaseModel):
    """Schema for creating a new thread."""
    title: str = Field(..., description="Title of the thread.")
    user_id: UUID = Field(..., description="UUID of the owner user.")

class ThreadOut(BaseModel):
    """Schema for thread response."""
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ThreadSummary(BaseModel):
    """Schema for thread list view summary."""
    id: UUID
    title: str
    last_updated: datetime = Field(..., validation_alias="updated_at")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
