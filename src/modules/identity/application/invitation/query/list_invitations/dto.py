from dataclasses import dataclass
from src.modules.identity.application.invitation.dto.invitation_view import (
    InvitationViewDTO,
)


@dataclass(frozen=True, slots=True)
class ListInvitationsResultDTO:
    invitations: list[InvitationViewDTO]
