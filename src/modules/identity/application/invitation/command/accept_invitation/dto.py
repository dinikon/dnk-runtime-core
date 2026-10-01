from dataclasses import dataclass
from uuid import UUID
from src.modules.identity.application.auth.port.session_store import SessionRecord


@dataclass(frozen=True, slots=True)
class AcceptInvitationResultDTO:
    tenant_id: UUID
    user_id: UUID
    session: SessionRecord
