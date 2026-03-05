from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class RequestEmailOtpRequestSchema(BaseModel):
    email: EmailStr


class ConfirmEmailOtpRequestSchema(BaseModel):
    email: EmailStr
    token: str
    code: str


class UpdateCurrentUserProfileRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_name: str
    first_name: str
    middle_name: str | None
    interface_language: Literal["uk", "en"]
    interface_theme: Literal["system", "dark", "light"] | None
    timezone: Literal["Europe/Kyiv", "Europe/Warsaw"]
