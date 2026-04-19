from pydantic import BaseModel, EmailStr


class ConfirmEmailOtpRequestSchema(BaseModel):
    """Pydantic-схема подтверждения email OTP."""

    email: EmailStr
    token: str
    code: str


__all__ = ["ConfirmEmailOtpRequestSchema"]
