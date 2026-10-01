from dataclasses import asdict
from src.modules.identity.application.auth.service.session_authentication import (
    SessionAuthenticationService,
)
from src.modules.identity.application.auth.service.session_issuer import SessionIssuer
from src.modules.identity.application.invitation.service.validator import (
    InvitationValidator,
)
from src.modules.identity.application.cloud.service.connection import (
    CloudConnectionService,
)
from src.modules.identity.application.access.query.list_users.handler import (
    ListUsersHandler,
)
from src.modules.identity.application.access.query.list_users.query import (
    ListUsersQuery,
)
from src.modules.identity.application.access.command.change_user_access.handler import (
    ChangeUserAccessHandler,
)
from src.modules.identity.application.access.command.change_user_access.command import (
    ChangeUserAccessCommand,
)
from src.modules.identity.application.invitation.query.list_invitations.handler import (
    ListInvitationsHandler,
)
from src.modules.identity.application.invitation.query.list_invitations.query import (
    ListInvitationsQuery,
)
from src.modules.identity.application.invitation.command.create_invitation.handler import (
    CreateInvitationHandler,
)
from src.modules.identity.application.invitation.command.create_invitation.command import (
    CreateInvitationCommand,
)
from src.modules.identity.application.invitation.command.revoke_invitation.handler import (
    RevokeInvitationHandler,
)
from src.modules.identity.application.invitation.command.revoke_invitation.command import (
    RevokeInvitationCommand,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.handler import (
    RequestInvitationOtpHandler,
)
from src.modules.identity.application.invitation.command.request_invitation_otp.command import (
    RequestInvitationOtpCommand,
)
from src.modules.identity.application.invitation.command.accept_invitation.handler import (
    AcceptInvitationHandler,
)
from src.modules.identity.application.invitation.command.accept_invitation.command import (
    AcceptInvitationCommand,
)
from src.modules.identity.application.cloud.query.get_cloud_status.handler import (
    GetCloudStatusHandler,
)
from src.modules.identity.application.cloud.query.get_cloud_status.query import (
    GetCloudStatusQuery,
)
from src.modules.identity.application.cloud.command.start_cloud_auth.handler import (
    StartCloudAuthHandler,
)
from src.modules.identity.application.cloud.command.start_cloud_auth.command import (
    StartCloudAuthCommand,
)
from src.modules.identity.application.cloud.command.complete_cloud_auth.handler import (
    CompleteCloudAuthHandler,
)
from src.modules.identity.application.cloud.command.complete_cloud_auth.command import (
    CompleteCloudAuthCommand,
)
from src.modules.identity.application.cloud.command.unlink_cloud_identity.handler import (
    UnlinkCloudIdentityHandler,
)
from src.modules.identity.application.cloud.command.unlink_cloud_identity.command import (
    UnlinkCloudIdentityCommand,
)

"Composition helpers for multi-step Identity integration scenarios."


class AccessScenarios:

    def __init__(self, **dependencies):
        self.__dict__.update(dependencies)
        self.authentication = SessionAuthenticationService(
            **{
                k: dependencies[k]
                for k in ("tenant_reader", "access", "sessions", "users")
            }
        )
        self.issuer = SessionIssuer(
            **{k: dependencies[k] for k in ("session_service", "settings", "sessions")}
        )
        self.invitations = InvitationValidator(access=self.access)

    async def principal(self, *args, **kwargs):
        return await self.authentication.principal(*args, **kwargs)

    async def issue_session(self, context, user):
        return await self.issuer.issue_session(context, user)

    def handler(self, name):
        handler, fields = HANDLERS[name]
        return handler(**{k: getattr(self, k) for k in fields})

    async def list_users(self, host, session_token):
        result = await self.handler("list_users").execute(
            ListUsersQuery(host=host, session_token=session_token)
        )
        return asdict(result)["users"]

    async def change_user(
        self, host, session_token, user_id, *, role=None, status=None
    ):
        result = await self.handler("change_user_access").execute(
            ChangeUserAccessCommand(
                host=host,
                session_token=session_token,
                user_id=user_id,
                role=role,
                status=status,
            )
        )
        return asdict(result)

    async def list_invitations(self, host, session_token):
        result = await self.handler("list_invitations").execute(
            ListInvitationsQuery(host=host, session_token=session_token)
        )
        return asdict(result)["invitations"]

    async def invite(self, host, session_token, email, role):
        result = await self.handler("create_invitation").execute(
            CreateInvitationCommand(
                host=host, session_token=session_token, email=email, role=role
            )
        )
        return asdict(result)

    async def revoke_invitation(self, host, session_token, invitation_id):
        result = await self.handler("revoke_invitation").execute(
            RevokeInvitationCommand(
                host=host, session_token=session_token, invitation_id=invitation_id
            )
        )
        return asdict(result)

    async def request_invitation_otp(self, host, invitation_token):
        result = await self.handler("request_invitation_otp").execute(
            RequestInvitationOtpCommand(host=host, invitation_token=invitation_token)
        )
        return asdict(result)

    async def accept_invitation(
        self, host, invitation_token, token, code, first_name, last_name
    ):
        result = await self.handler("accept_invitation").execute(
            AcceptInvitationCommand(
                host=host,
                invitation_token=invitation_token,
                token=token,
                code=code,
                first_name=first_name,
                last_name=last_name,
            )
        )
        context = await self.tenant_reader.get_by_host(host)
        from src.modules.identity.domain.user.value_object.user_id import UserIdVO
        from src.modules.shared import EntityIdVO

        user = await self.users.get_by_id(
            UserIdVO.from_value(result.user_id),
            tenant_id=EntityIdVO.from_value(result.tenant_id),
        )
        return (context, user, result.session)


class CloudScenarios(AccessScenarios):

    def __init__(self, local, connections, oidc):
        self.__dict__.update(local.__dict__)
        self.connections, self.oidc = (connections, oidc)
        self.cloud_connection = CloudConnectionService(connections=connections)

    async def status(self, host, session_token):
        result = await self.handler("get_cloud_status").execute(
            GetCloudStatusQuery(host=host, session_token=session_token)
        )
        return asdict(result)

    async def start(self, host, session_token, flow_cookie, purpose):
        result = await self.handler("start_cloud_auth").execute(
            StartCloudAuthCommand(
                host=host,
                session_token=session_token,
                flow_cookie=flow_cookie,
                purpose=purpose,
            )
        )
        return asdict(result)

    async def callback(
        self, host, session_token, flow_cookie, *, state, code, issuer, error=None
    ):
        result = await self.handler("complete_cloud_auth").execute(
            CompleteCloudAuthCommand(
                host=host,
                session_token=session_token,
                flow_cookie=flow_cookie,
                state=state,
                code=code,
                issuer=issuer,
                error=error,
            )
        )
        return (result.purpose, result.session)

    async def unlink(self, host, session_token):
        result = await self.handler("unlink_cloud_identity").execute(
            UnlinkCloudIdentityCommand(host=host, session_token=session_token)
        )
        return asdict(result)


HANDLERS = {
    "list_users": (ListUsersHandler, ["access", "authentication"]),
    "change_user_access": (
        ChangeUserAccessHandler,
        ["access", "authentication", "projections", "uow", "users"],
    ),
    "list_invitations": (ListInvitationsHandler, ["access", "authentication"]),
    "create_invitation": (
        CreateInvitationHandler,
        ["access", "authentication", "email", "settings", "uow", "users"],
    ),
    "revoke_invitation": (RevokeInvitationHandler, ["access", "authentication", "uow"]),
    "request_invitation_otp": (
        RequestInvitationOtpHandler,
        ["email", "invitations", "otp", "settings", "tenant_reader", "tokens"],
    ),
    "accept_invitation": (
        AcceptInvitationHandler,
        [
            "access",
            "invitations",
            "issuer",
            "otp",
            "tenant_reader",
            "tokens",
            "uow",
            "users",
        ],
    ),
    "get_cloud_status": (
        GetCloudStatusHandler,
        ["access", "authentication", "connections", "tenant_reader"],
    ),
    "start_cloud_auth": (
        StartCloudAuthHandler,
        [
            "access",
            "authentication",
            "cloud_connection",
            "oidc",
            "tenant_reader",
            "tokens",
        ],
    ),
    "complete_cloud_auth": (
        CompleteCloudAuthHandler,
        [
            "access",
            "authentication",
            "cloud_connection",
            "issuer",
            "oidc",
            "projections",
            "tenant_reader",
            "tokens",
            "uow",
            "users",
        ],
    ),
    "unlink_cloud_identity": (
        UnlinkCloudIdentityHandler,
        ["access", "authentication", "projections", "uow"],
    ),
}
