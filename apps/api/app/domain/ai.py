"""AI assistant contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatCitation(BaseModel):
    label: str
    source_type: str
    source_id: str | None = None
    source_title: str | None = None
    snippet: str | None = None


class ChatResponseData(BaseModel):
    response: str
    sources: list[ChatCitation] = Field(default_factory=list)


class SuggestedPrompt(BaseModel):
    label: str
    query: str
