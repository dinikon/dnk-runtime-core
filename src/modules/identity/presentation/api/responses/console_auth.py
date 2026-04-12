from uuid import UUID

from pydantic import BaseModel, Field


class RequestEmailOtpResponseSchema(BaseModel):
    """Pydantic-схема ответа на запрос email OTP."""

    token: str
    expires_in: int
    code: str | None = None


class ConfirmEmailOtpResponseSchema(BaseModel):
    """Pydantic-схема ответа подтверждения email OTP."""

    ok: bool
    user_id: UUID
    tenant_id: UUID


class LogoutCurrentSessionResponseSchema(BaseModel):
    """Pydantic-схема ответа logout текущей session."""

    ok: bool


class CurrentUserEmailResponseSchema(BaseModel):
    """Pydantic-схема email текущего пользователя."""

    id: UUID
    email: str
    is_primary: bool
    is_verified: bool


class CurrentUserResponseSchema(BaseModel):
    """Pydantic-схема профиля текущего пользователя."""

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
