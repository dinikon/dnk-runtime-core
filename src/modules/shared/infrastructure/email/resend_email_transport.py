from __future__ import annotations

from src.modules.shared.domain.email.email_provider_not_implemented_error import (
    EmailProviderNotImplementedError,
)
from src.modules.shared.infrastructure.email.email_transport_port import (
    EmailTransportPort,
)
from src.modules.shared.infrastructure.email.rendered_email_message import (
    RenderedEmailMessage,
)


class ResendEmailTransport(EmailTransportPort):
    """Placeholder-transport для будущего провайдера Resend."""

    async def send(self, message: RenderedEmailMessage) -> None:
        """Падает при попытке отправки, пока провайдер не реализован."""
        raise EmailProviderNotImplementedError(
            "Email provider 'resend' is not implemented yet."
        )


__all__ = ["ResendEmailTransport"]
