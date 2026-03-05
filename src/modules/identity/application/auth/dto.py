from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class GetCurrentUserCommandDTO:
    host: str
    session_token: str | None


@dataclass(frozen=True, slots=True)
class GetCurrentUserEmailDTO:
    id: UUID
    email: str
    is_primary: bool
    is_verified: bool


@dataclass(frozen=True, slots=True)
class GetCurrentUserResultDTO:
    id: UUID
    status: str
    last_name: str
    first_name: str
    middle_name: str | None
    avatar: str | None
    interface_language: str
    interface_theme: str | None
    timezone: str
    emails: list[GetCurrentUserEmailDTO] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserProfileCommandDTO:
    host: str
    session_token: str | None
    last_name: str
    first_name: str
    middle_name: str | None
    interface_language: str
    interface_theme: str | None
    timezone: str


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserProfileResultDTO:
    id: UUID
    status: str
    last_name: str
    first_name: str
    middle_name: str | None
    avatar: str | None
    interface_language: str
    interface_theme: str | None
    timezone: str
    emails: list[GetCurrentUserEmailDTO] = field(default_factory=list)
