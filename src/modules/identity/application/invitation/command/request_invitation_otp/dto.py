from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestInvitationOtpResultDTO:
    token: str
    expires_in: int
    code: str
