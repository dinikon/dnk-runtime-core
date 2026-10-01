from datetime import UTC, datetime, timedelta
import hashlib
import logging
import secrets
from uuid import uuid4
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.application.invitation.dto.invitation import Invitation
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.email import EmailDeliveryError
from src.modules.identity.application.email.send_invitation_variables import (
    SendInvitationVariables,
)
from src.modules.identity.application.email.system_email_kind import SystemEmailKind
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.application.email.email_service_port import EmailServicePort
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.config.feature.identity.auth_config import IdentityAuthSettings
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.invitation.service.view import invitation_view
from src.modules.identity.application.invitation.command.create_invitation.command import (
    CreateInvitationCommand,
)
from src.modules.identity.application.invitation.command.create_invitation.dto import (
    CreateInvitationResultDTO,
)

log = logging.getLogger(__name__)


class CreateInvitationHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
        email: EmailServicePort,
        settings: IdentityAuthSettings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
    ) -> None:
        self.access = access
        self.authentication = authentication
        self.email = email
        self.settings = settings
        self.uow = uow
        self.users = users

    async def execute(
        self, request: CreateInvitationCommand
    ) -> CreateInvitationResultDTO:
        host = request.host
        session_token = request.session_token
        email = request.email
        role = request.role
        context, user, _ = await self.authentication.principal(
            host, session_token, admin=True, locked=True
        )
        email = email.strip().lower()
        if role not in {"admin", "member"}:
            raise IdentityAccessError("Invalid role.", 422)
        if await self.users.exists_by_tenant_and_email(
            EntityIdVO.from_value(context.tenant_id), email
        ):
            raise IdentityAccessError(
                "This email already belongs to a workspace user.", 409
            )
        now = datetime.now(UTC)
        for old in await self.access.invitations(context.tenant_id):
            if old.email == email and old.state == "pending" and (old.expires_at > now):
                raise IdentityAccessError(
                    "A pending invitation already exists for this email.", 409
                )
        token = secrets.token_urlsafe(32)
        invitation = Invitation(
            uuid4(),
            email,
            role,
            hashlib.sha256(token.encode()).hexdigest(),
            "pending",
            user.id.uuid,
            None,
            now,
            now + timedelta(days=7),
        )
        await self.access.add_invitation(context.tenant_id, invitation)
        await self.uow.commit()
        scheme = "http" if self.settings.allow_insecure_http else "https"
        invitation_url = f"{scheme}://{context.host}/accept-invitation#token={token}"
        variables: SendInvitationVariables = {"invitation_url": invitation_url}
        try:
            await self.email.send(SystemEmailKind.SEND_INVITATION, email, variables)
        except EmailDeliveryError:
            log.exception(
                "Failed to deliver invitation email to '%s' for tenant '%s'.",
                email,
                context.tenant_id,
            )
        view = invitation_view(invitation)
        return CreateInvitationResultDTO(
            id=view.id,
            email=view.email,
            role=view.role,
            state=view.state,
            expires_at=view.expires_at,
            invitation_url=invitation_url,
        )
