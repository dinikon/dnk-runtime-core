import hashlib
from uuid import UUID
from src.modules.identity.domain.access.error import IdentityAccessError
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared import EntityIdVO
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.cloud.port.cloud import AccessProjectionWriterPort
from src.modules.identity.application.cloud.port.oidc import OidcClientPort
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.auth.service.session_issuer import SessionIssuer
from src.modules.identity.application.cloud.service.connection import (
    CloudConnectionService,
)
from src.modules.identity.application.cloud.command.complete_cloud_auth.command import (
    CompleteCloudAuthCommand,
)
from src.modules.identity.application.cloud.command.complete_cloud_auth.dto import (
    CompleteCloudAuthResultDTO,
)


class CompleteCloudAuthHandler:

    def __init__(
        self,
        *,
        access: AccessRepositoryProtocol,
        authentication: SessionAuthenticationService,
        cloud_connection: CloudConnectionService,
        issuer: SessionIssuer,
        oidc: OidcClientPort,
        projections: AccessProjectionWriterPort,
        tenant_reader: TenantContextReaderPort,
        tokens: TokenManager,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
    ) -> None:
        self.access = access
        self.authentication = authentication
        self.cloud_connection = cloud_connection
        self.issuer = issuer
        self.oidc = oidc
        self.projections = projections
        self.tenant_reader = tenant_reader
        self.tokens = tokens
        self.uow = uow
        self.users = users

    async def execute(
        self, request: CompleteCloudAuthCommand
    ) -> CompleteCloudAuthResultDTO:
        host = request.host
        session_token = request.session_token
        flow_cookie = request.flow_cookie
        state = request.state
        code = request.code
        issuer = request.issuer
        error = request.error
        context = await self.tenant_reader.get_by_host(host)
        saved = await self.tokens.consume_token(
            prefix="oidc_state", suffix=str(context.tenant_id), token=state
        )
        if (
            saved is None
            or not flow_cookie
            or saved.get("flow_cookie") != flow_cookie
            or (saved.get("host") != context.host)
            or (saved.get("domain_id") != str(context.tenant_domain_id))
            or (saved.get("tenant_id") != str(context.tenant_id))
        ):
            raise IdentityAccessError(
                "Cloud authorization state is invalid or expired.", 401
            )
        if (
            saved.get("session_fingerprint")
            != hashlib.sha256((session_token or "").encode()).hexdigest()
        ):
            raise IdentityAccessError("The authorization session has changed.", 401)
        connection = await self.cloud_connection.connection(context)
        if (
            issuer != connection.issuer
            or saved.get("issuer") != connection.issuer
            or saved.get("client_id") != connection.client_id
        ):
            raise IdentityAccessError("Cloud authorization issuer does not match.", 401)
        if error or not code:
            raise IdentityAccessError("Cloud authorization was not completed.", 401)
        subject = await self.oidc.exchange(
            connection, code=code, nonce=saved["nonce"], verifier=saved["verifier"]
        )
        await self.access.lock(context.tenant_id)
        if saved["purpose"] == "link":
            context, user, session = await self.authentication.principal(
                host, session_token
            )
            if (
                str(user.id.uuid) != saved["user_id"]
                or session.session_id != saved["session_id"]
                or user.session_epoch != saved["epoch"]
            ):
                raise IdentityAccessError("The linking session has changed.", 401)
            if not any(
                (
                    e.is_verified and e.is_primary and (not e.is_deleted)
                    for e in user.emails
                )
            ):
                raise IdentityAccessError("Verified local email is required.", 403)
            await self.access.bind(
                context.tenant_id, user.id.uuid, connection.issuer, subject
            )
            await self.projections.set_available(
                context.tenant_id, UUID(subject), True, user.role
            )
            await self.uow.commit()
            return CompleteCloudAuthResultDTO("link", None)
        identity = await self.access.identity_for_subject(
            context.tenant_id, connection.issuer, subject
        )
        if identity is None:
            raise IdentityAccessError(
                "This cloud account has no local workspace access.", 403
            )
        user = await self.users.get_by_id(
            UserIdVO.from_value(identity.user_id),
            tenant_id=EntityIdVO.from_value(context.tenant_id),
        )
        if user is None or not user.can_login():
            raise IdentityAccessError("Local workspace access is unavailable.", 403)
        await self.uow.commit()
        session = await self.issuer.issue_session(context, user)
        return CompleteCloudAuthResultDTO("login", session)
