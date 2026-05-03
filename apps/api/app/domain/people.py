"""People module domain contracts."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    title: str | None = None
    department: str | None = None
    market: str | None = None
    timezone: str | None = None
    role: str | None = None
    phone: str | None = None


class InviteCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=200)
    role: str = "initiative_owner"
    title: str | None = None
    department: str | None = None
    market: str | None = None
    workstream_ids: list[str] = Field(default_factory=list)


class WorkstreamAssignment(BaseModel):
    workstream_ids: list[str]
