from __future__ import annotations

from src.modules.shared.infrastructure.email.models import RenderedEmailMessage
from src.modules.shared.infrastructure.email.ports import EmailTransportPort
from src.modules.shared.kernel.email.errors import EmailProviderNotImplementedError


class ResendEmailTransport(EmailTransportPort):
    """Placeholder-transport для будущего провайдера Resend."""

    async def send(self, message: RenderedEmailMessage) -> None:
        """Падает при попытке отправки, пока провайдер не реализован."""
        raise EmailProviderNotImplementedError(
            "Email provider 'resend' is not implemented yet."
        )


__all__ = ["ResendEmailTransport"]
