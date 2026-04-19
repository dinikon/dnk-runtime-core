from pydantic import BaseModel


class RequestEmailOtpResponseSchema(BaseModel):
    """Pydantic-схема ответа на запрос email OTP."""

    token: str
    expires_in: int
    code: str | None = None


__all__ = ["RequestEmailOtpResponseSchema"]
