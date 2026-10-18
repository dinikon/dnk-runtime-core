from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestInvitationOtpCommand:
    host: str
    invitation_token: str
