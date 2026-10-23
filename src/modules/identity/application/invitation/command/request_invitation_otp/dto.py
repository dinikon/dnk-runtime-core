from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestInvitationOtpResultDTO:
    """Результат OTP приглашения; открытый код доступен только в Development."""

    token: str
    expires_in: int
    code: str | None = None
