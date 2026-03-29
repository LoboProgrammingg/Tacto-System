"""Chat HTTP Schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for chat test endpoint."""

    restaurant_id: UUID = Field(..., description="Restaurant UUID")
    message: str = Field(..., min_length=1, max_length=4096)
    customer_phone: str = Field(
        default="5511999999999",
        description="Simulated phone — keeps conversation context across calls",
    )
    customer_name: str | None = Field(default=None)


class ChatMessage(BaseModel):
    """A single message in chat history."""

    role: str  # "user" | "assistant"
    content: str


class ChatResponse(BaseModel):
    """Response from chat test endpoint."""

    response: str
    restaurant_name: str
    conversation_id: str
    processing_time_ms: int
    history: list[ChatMessage]
