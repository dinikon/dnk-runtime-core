from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class RequestEmailOtpRequestSchema(BaseModel):
    """Pydantic-схема запроса email OTP."""

    email: EmailStr


class ConfirmEmailOtpRequestSchema(BaseModel):
    """Pydantic-схема подтверждения email OTP."""

    email: EmailStr
    token: str
    code: str


class UpdateCurrentUserProfileRequestSchema(BaseModel):
    """Pydantic-схема обновления профиля текущего пользователя."""

    model_config = ConfigDict(extra="forbid")

    last_name: str
    first_name: str
    middle_name: str | None
    interface_language: Literal["uk", "en"]
    interface_theme: Literal["system", "dark", "light"] | None
    timezone: Literal["Europe/Kyiv", "Europe/Warsaw"]
