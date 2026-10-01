from src.config.infrastructure.email_config import EmailProvider, EmailSettings
from src.modules.shared.application.email.email_transport_port import EmailTransportPort
from src.modules.shared.infrastructure.email.resend_email_transport import (
    ResendEmailTransport,
)
from src.modules.shared.infrastructure.email.smtp_email_transport import (
    SmtpEmailTransport,
)


def build_email_transport(settings: EmailSettings) -> EmailTransportPort:
    """Собирает транспорт доставки без знания видов и шаблонов писем."""
    if settings.provider == EmailProvider.RESEND:
        return ResendEmailTransport()
    return SmtpEmailTransport.from_settings(settings)
