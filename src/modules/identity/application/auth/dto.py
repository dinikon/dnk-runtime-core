from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestEmailOtpCommandDTO:
    host: str
    email: str


@dataclass(frozen=True, slots=True)
class RequestEmailOtpResultDTO:
    token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class ConfirmEmailOtpCommandDTO:
    host: str
    email: str
    token: str
    code: str


@dataclass(frozen=True, slots=True)
class ConfirmEmailOtpResultDTO:
    ok: bool
    user_id: UUID
    tenant_id: UUID
    session_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class LogoutCurrentSessionCommandDTO:
    host: str
    session_token: str | None


@dataclass(frozen=True, slots=True)
class LogoutCurrentSessionResultDTO:
    ok: bool
