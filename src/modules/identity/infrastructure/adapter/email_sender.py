from __future__ import annotations

from dataclasses import dataclass

from src.modules.identity.application.ports import EmailSenderPort


@dataclass(frozen=True, slots=True)
class SentLoginCode:
    """Запись отправленного login code для in-memory email sender."""

    email: str
    code: str


class InMemoryEmailSender(EmailSenderPort):
    """Email sender-заглушка, сохраняющая отправленные login codes в памяти."""

    def __init__(self) -> None:
        """Инициализирует список отправленных codes."""
        self.sent_codes: list[SentLoginCode] = []

    async def send_login_code(self, email: str, code: str) -> None:
        """Сохраняет login code в памяти вместо реальной отправки email."""
        self.sent_codes.append(SentLoginCode(email=email, code=code))


default_email_sender = InMemoryEmailSender()


__all__ = ["InMemoryEmailSender", "SentLoginCode", "default_email_sender"]
