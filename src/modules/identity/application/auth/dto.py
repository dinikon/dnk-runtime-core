from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestEmailOtpCommandDTO:
    """DTO команды запроса email OTP для входа."""

    host: str
    email: str


@dataclass(frozen=True, slots=True)
class RequestEmailOtpResultDTO:
    """DTO результата создания OTP challenge."""

    token: str
    expires_in: int
    code: str | None = None


@dataclass(frozen=True, slots=True)
class ConfirmEmailOtpCommandDTO:
    """DTO команды подтверждения email OTP."""

    host: str
    email: str
    token: str
    code: str


@dataclass(frozen=True, slots=True)
class ConfirmEmailOtpResultDTO:
    """DTO результата подтверждения OTP и создания session."""

    ok: bool
    user_id: UUID
    tenant_id: UUID
    session_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class LogoutCurrentSessionCommandDTO:
    """DTO команды logout текущей session."""

    host: str
    session_token: str | None


@dataclass(frozen=True, slots=True)
class LogoutCurrentSessionResultDTO:
    """DTO результата logout текущей session."""

    ok: bool


@dataclass(frozen=True, slots=True)
class GetCurrentUserCommandDTO:
    """DTO команды получения текущего пользователя по session."""

    host: str
    session_token: str | None


@dataclass(frozen=True, slots=True)
class GetCurrentUserEmailDTO:
    """DTO email-адреса текущего пользователя."""

    id: UUID
    email: str
    is_primary: bool
    is_verified: bool


@dataclass(frozen=True, slots=True)
class GetCurrentUserResultDTO:
    """DTO профиля текущего пользователя."""

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
    """DTO команды обновления профиля текущего пользователя."""

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
    """DTO результата обновления профиля текущего пользователя."""

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
