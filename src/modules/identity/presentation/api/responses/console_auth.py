from uuid import UUID

from pydantic import BaseModel, Field


class RequestEmailOtpResponseSchema(BaseModel):
    token: str
    expires_in: int


class ConfirmEmailOtpResponseSchema(BaseModel):
    ok: bool
    user_id: UUID
    tenant_id: UUID


class LogoutCurrentSessionResponseSchema(BaseModel):
    ok: bool


class CurrentUserEmailResponseSchema(BaseModel):
    id: UUID
    email: str
    is_primary: bool
    is_verified: bool


class CurrentUserResponseSchema(BaseModel):
    id: UUID
    status: str
    last_name: str
    first_name: str
    middle_name: str | None
    avatar: str | None
    interface_language: str
    interface_theme: str | None
    timezone: str
    emails: list[CurrentUserEmailResponseSchema] = Field(default_factory=list)
