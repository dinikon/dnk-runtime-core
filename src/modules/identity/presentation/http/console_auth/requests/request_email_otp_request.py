from pydantic import BaseModel, EmailStr


class RequestEmailOtpRequestSchema(BaseModel):
    """Pydantic-схема запроса email OTP."""

    email: EmailStr


__all__ = ["RequestEmailOtpRequestSchema"]
