"""HTTP API 请求与响应模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    tools: list[dict[str, object]] = Field(default_factory=list)


class MessageResponse(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    message_count: int
    updated_at: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    memory: Literal["sqlite"] = "sqlite"

