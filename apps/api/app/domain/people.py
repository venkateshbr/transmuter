"""People module domain contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

PlatformRole = Literal[
    "transformation_office",
    "tenant_admin",
    "pmo_lead",
    "finance_lead",
    "workstream_lead",
    "initiative_owner",
    "business_benefit_owner",
    "executive_sponsor",
    "viewer",
]


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    title: str | None = None
    department: str | None = None
    market: str | None = None
    timezone: str | None = None
    role: PlatformRole | None = None
    phone: str | None = None


class InviteCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=200)
    role: PlatformRole = "initiative_owner"
    title: str | None = None
    department: str | None = None
    market: str | None = None
    workstream_ids: list[str] = Field(default_factory=list)


class InviteAccept(BaseModel):
    token: str = Field(..., min_length=32, max_length=512)
    password: str = Field(..., min_length=12, max_length=256)
    confirm_password: str = Field(..., min_length=12, max_length=256)


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=200)
    role: PlatformRole = "initiative_owner"
    temporary_password: str = Field(..., min_length=12, max_length=256)
    title: str | None = None
    department: str | None = None
    market: str | None = None
    workstream_ids: list[str] = Field(default_factory=list)


class UserTemporaryPassword(BaseModel):
    temporary_password: str = Field(..., min_length=12, max_length=256)


class WorkstreamAssignment(BaseModel):
    workstream_ids: list[str]
