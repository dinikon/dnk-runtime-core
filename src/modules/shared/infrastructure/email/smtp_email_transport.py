from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from src.config.infrastructure.email_config import EmailSettings
from src.modules.shared.domain.email.email_delivery_error import EmailDeliveryError
from src.modules.shared.infrastructure.email.email_transport_port import (
    EmailTransportPort,
)
from src.modules.shared.infrastructure.email.rendered_email_message import (
    RenderedEmailMessage,
)


class SmtpEmailTransport(EmailTransportPort):
    """SMTP transport для already-rendered системных email-писем."""

    def __init__(
        self,
        *,
        from_address: str,
        from_name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        use_starttls: bool,
        timeout_seconds: float,
    ) -> None:
        self._from_address = from_address
        self._from_name = from_name
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._use_starttls = use_starttls
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: EmailSettings) -> "SmtpEmailTransport":
        """Создает SMTP transport из email settings."""
        smtp = settings.smtp
        return cls(
            from_address=settings.from_address,
            from_name=settings.from_name,
            host=smtp.host,
            port=smtp.port,
            username=smtp.username,
            password=smtp.password,
            use_tls=smtp.use_tls,
            use_starttls=smtp.use_starttls,
            timeout_seconds=smtp.timeout_seconds,
        )

    async def send(self, message: RenderedEmailMessage) -> None:
        """Отправляет письмо через SMTP в отдельном thread."""
        try:
            await asyncio.to_thread(self._send_blocking, message)
        except EmailDeliveryError:
            raise
        except Exception as exc:
            raise EmailDeliveryError(
                f"Failed to send email to '{message.recipient_email}'."
            ) from exc

    def _send_blocking(self, message: RenderedEmailMessage) -> None:
        email_message = self._build_email_message(message)
        smtp_client_cls = smtplib.SMTP_SSL if self._use_tls else smtplib.SMTP

        with smtp_client_cls(
            self._host,
            self._port,
            timeout=self._timeout_seconds,
        ) as client:
            if self._use_starttls and not self._use_tls:
                client.starttls()
            if self._username or self._password:
                client.login(self._username, self._password)
            client.send_message(email_message)

    def _build_email_message(self, message: RenderedEmailMessage) -> EmailMessage:
        """Собирает stdlib EmailMessage из rendered письма."""
        email_message = EmailMessage()
        email_message["To"] = message.recipient_email
        email_message["From"] = self._format_sender()
        email_message["Subject"] = message.subject
        email_message.set_content(message.text_body)
        if message.html_body is not None:
            email_message.add_alternative(message.html_body, subtype="html")
        return email_message

    def _format_sender(self) -> str:
        """Форматирует sender для email headers."""
        if self._from_name:
            return formataddr((self._from_name, self._from_address))
        return self._from_address


__all__ = ["SmtpEmailTransport"]
