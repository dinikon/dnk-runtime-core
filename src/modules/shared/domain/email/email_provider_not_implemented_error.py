from src.modules.shared.domain.email.email_delivery_error import EmailDeliveryError


class EmailProviderNotImplementedError(EmailDeliveryError):
    """Провайдер email-доставки объявлен, но еще не реализован."""


__all__ = ["EmailProviderNotImplementedError"]
