from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RevokeInvitationResultDTO:
    ok: bool = True
