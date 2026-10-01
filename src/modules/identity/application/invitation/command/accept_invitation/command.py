from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AcceptInvitationCommand:
    host: str
    invitation_token: str
    token: str
    code: str
    first_name: str
    last_name: str
