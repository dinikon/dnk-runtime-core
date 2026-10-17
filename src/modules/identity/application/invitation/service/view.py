from src.modules.identity.application.invitation.dto.invitation import Invitation
from datetime import datetime, UTC
from src.modules.identity.application.invitation.dto.invitation_view import (
    InvitationViewDTO,
)


def invitation_view(invitation: Invitation) -> InvitationViewDTO:
    state = invitation.state
    if state == "pending" and invitation.expires_at <= datetime.now(UTC):
        state = "expired"
    return InvitationViewDTO(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        state=state,
        expires_at=invitation.expires_at,
    )
