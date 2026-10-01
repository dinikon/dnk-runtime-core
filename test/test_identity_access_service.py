from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from src.modules.identity.application.invitation.command.create_invitation.handler import (
    CreateInvitationHandler,
)
from src.modules.identity.application.invitation.command.create_invitation.command import (
    CreateInvitationCommand,
)
from src.modules.shared.domain.email import EmailDeliveryError
from src.modules.identity.application.email.system_email_kind import SystemEmailKind


class IdentityAccessServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tenant_id = uuid4()
        self.context = SimpleNamespace(
            tenant_id=self.tenant_id,
            tenant_domain_id=uuid4(),
            host="tenant.example",
        )
        self.admin = SimpleNamespace(id=SimpleNamespace(uuid=uuid4()))
        self.uow = AsyncMock()
        self.users = AsyncMock()
        self.users.exists_by_tenant_and_email.return_value = False
        self.access = AsyncMock()
        self.access.invitations.return_value = []
        self.email = AsyncMock()
        self.authentication = AsyncMock()
        self.authentication.principal.return_value = (self.context, self.admin, None)
        self.service = CreateInvitationHandler(
            uow=self.uow,
            users=self.users,
            access=self.access,
            authentication=self.authentication,
            email=self.email,
            settings=SimpleNamespace(allow_insecure_http=False),
        )

    async def test_invite_commits_then_emails_the_returned_link(self) -> None:
        events: list[str] = []

        async def commit() -> None:
            events.append("commit")

        async def send(*_args) -> None:
            events.append("send")

        self.uow.commit.side_effect = commit
        self.email.send.side_effect = send

        result = await self.service.execute(
            CreateInvitationCommand(
                "tenant.example",
                "session-token",
                " Guest@Example.COM ",
                "member",
            )
        )

        self.assertEqual(events, ["commit", "send"])
        self.assertEqual(result.email, "guest@example.com")
        self.email.send.assert_awaited_once_with(
            SystemEmailKind.SEND_INVITATION,
            "guest@example.com",
            {"invitation_url": result.invitation_url},
        )

    async def test_invite_remains_pending_when_email_delivery_fails(self) -> None:
        self.email.send.side_effect = EmailDeliveryError("SMTP is unavailable.")

        with self.assertLogs(
            "src.modules.identity.application.invitation.command.create_invitation.handler",
            level="ERROR",
        ) as captured:
            result = await self.service.execute(
                CreateInvitationCommand(
                    "tenant.example",
                    "session-token",
                    "guest@example.com",
                    "member",
                )
            )

        self.uow.commit.assert_awaited_once_with()
        invitation = self.access.add_invitation.await_args.args[1]
        self.assertEqual(invitation.state, "pending")
        self.assertEqual(invitation.email, "guest@example.com")
        self.assertEqual(result.state, "pending")
        self.assertTrue(result.invitation_url)
        self.assertNotIn(result.invitation_url, "\n".join(captured.output))


__all__ = ["IdentityAccessServiceTests"]
