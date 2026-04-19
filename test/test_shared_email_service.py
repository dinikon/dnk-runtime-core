from __future__ import annotations

import unittest
from unittest.mock import patch

from src.config.infrastructure.email_config import (
    EmailProvider,
    EmailSettings,
    EmailSmtpSettings,
)
from src.modules.shared.depends.email_service import build_email_service
from src.modules.shared.infrastructure.email import (
    SmtpEmailTransport,
    SystemEmailService,
)
from src.modules.shared.infrastructure.email.models import RenderedEmailMessage
from src.modules.shared.kernel.email import (
    EmailProviderNotImplementedError,
    SendOtpCodeVariables,
    SystemEmailKind,
)


class _EmailTransportStub:
    def __init__(self) -> None:
        self.sent: list[RenderedEmailMessage] = []

    async def send(self, message: RenderedEmailMessage) -> None:
        self.sent.append(message)


class _SmtpClientStub:
    instances: list["_SmtpClientStub"] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in: tuple[str, str] | None = None
        self.sent_message = None
        self.__class__.instances.append(self)

    def __enter__(self) -> "_SmtpClientStub":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def send_message(self, message) -> None:
        self.sent_message = message


class SharedEmailServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_build_email_service_returns_system_email_service_for_smtp_provider(
        self,
    ) -> None:
        service = build_email_service(
            EmailSettings(
                provider=EmailProvider.SMTP,
                smtp=EmailSmtpSettings(host="smtp.example.com"),
            )
        )

        self.assertIsInstance(service, SystemEmailService)

    async def test_system_email_service_renders_send_otp_code_message(self) -> None:
        transport = _EmailTransportStub()
        service = SystemEmailService(transport)
        variables: SendOtpCodeVariables = {"otp_code": "123456"}

        await service.send(
            SystemEmailKind.SEND_OTP_CODE,
            "john@example.com",
            variables,
        )

        rendered = transport.sent[0]
        self.assertEqual(rendered.recipient_email, "john@example.com")
        self.assertEqual(rendered.subject, "Your sign-in code")
        self.assertIn("123456", rendered.text_body)
        self.assertIsNone(rendered.html_body)

    async def test_resend_transport_raises_not_implemented_when_service_sends_email(
        self,
    ) -> None:
        service = build_email_service(EmailSettings(provider=EmailProvider.RESEND))

        with self.assertRaises(EmailProviderNotImplementedError):
            await service.send(
                SystemEmailKind.SEND_OTP_CODE,
                "john@example.com",
                {"otp_code": "123456"},
            )

    def test_smtp_transport_builds_plain_text_email_message(self) -> None:
        transport = SmtpEmailTransport(
            from_address="no-reply@example.com",
            from_name="DNK Runtime",
            host="smtp.example.com",
            port=25,
            username="",
            password="",
            use_tls=False,
            use_starttls=False,
            timeout_seconds=10.0,
        )

        message = transport._build_email_message(
            RenderedEmailMessage(
                recipient_email="john@example.com",
                subject="Your sign-in code",
                text_body="Your code: 123456",
            )
        )

        self.assertEqual(message["To"], "john@example.com")
        self.assertEqual(message["Subject"], "Your sign-in code")
        self.assertEqual(message.get_content_type(), "text/plain")
        self.assertEqual(message.get_content().strip(), "Your code: 123456")

    def test_smtp_transport_builds_multipart_message_when_html_body_present(
        self,
    ) -> None:
        transport = SmtpEmailTransport(
            from_address="no-reply@example.com",
            from_name="DNK Runtime",
            host="smtp.example.com",
            port=25,
            username="",
            password="",
            use_tls=False,
            use_starttls=False,
            timeout_seconds=10.0,
        )

        message = transport._build_email_message(
            RenderedEmailMessage(
                recipient_email="john@example.com",
                subject="Your sign-in code",
                text_body="Your code: 123456",
                html_body="<p>Your code: <strong>123456</strong></p>",
            )
        )

        self.assertEqual(message.get_content_type(), "multipart/alternative")
        parts = list(message.iter_parts())
        self.assertEqual(parts[0].get_content_type(), "text/plain")
        self.assertEqual(parts[1].get_content_type(), "text/html")

    async def test_smtp_transport_uses_plain_smtp_and_starttls_when_configured(
        self,
    ) -> None:
        _SmtpClientStub.instances.clear()
        transport = SmtpEmailTransport(
            from_address="no-reply@example.com",
            from_name="DNK Runtime",
            host="smtp.example.com",
            port=587,
            username="user",
            password="secret",
            use_tls=False,
            use_starttls=True,
            timeout_seconds=5.0,
        )

        with (
            patch(
                "src.modules.shared.infrastructure.email.smtp_email_transport.smtplib.SMTP",
                _SmtpClientStub,
            ),
            patch(
                "src.modules.shared.infrastructure.email.smtp_email_transport.smtplib.SMTP_SSL",
                _SmtpClientStub,
            ),
        ):
            await transport.send(
                RenderedEmailMessage(
                    recipient_email="john@example.com",
                    subject="OTP",
                    text_body="Your code: 123456",
                )
            )

        client = _SmtpClientStub.instances[0]
        self.assertEqual(client.host, "smtp.example.com")
        self.assertEqual(client.port, 587)
        self.assertTrue(client.started_tls)
        self.assertEqual(client.logged_in, ("user", "secret"))

    async def test_smtp_transport_uses_smtp_ssl_when_tls_enabled(self) -> None:
        smtp_instances: list[_SmtpClientStub] = []
        smtp_ssl_instances: list[_SmtpClientStub] = []

        def _smtp_factory(host: str, port: int, timeout: float) -> _SmtpClientStub:
            client = _SmtpClientStub(host, port, timeout)
            smtp_instances.append(client)
            return client

        def _smtp_ssl_factory(host: str, port: int, timeout: float) -> _SmtpClientStub:
            client = _SmtpClientStub(host, port, timeout)
            smtp_ssl_instances.append(client)
            return client

        transport = SmtpEmailTransport(
            from_address="no-reply@example.com",
            from_name="DNK Runtime",
            host="smtp.example.com",
            port=465,
            username="",
            password="",
            use_tls=True,
            use_starttls=False,
            timeout_seconds=5.0,
        )

        with (
            patch(
                "src.modules.shared.infrastructure.email.smtp_email_transport.smtplib.SMTP",
                side_effect=_smtp_factory,
            ),
            patch(
                "src.modules.shared.infrastructure.email.smtp_email_transport.smtplib.SMTP_SSL",
                side_effect=_smtp_ssl_factory,
            ),
        ):
            await transport.send(
                RenderedEmailMessage(
                    recipient_email="john@example.com",
                    subject="OTP",
                    text_body="Your code: 123456",
                )
            )

        self.assertEqual(smtp_instances, [])
        self.assertEqual(len(smtp_ssl_instances), 1)


__all__ = ["SharedEmailServiceTests"]
