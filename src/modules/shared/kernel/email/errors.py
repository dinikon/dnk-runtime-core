from __future__ import annotations


class EmailDeliveryError(RuntimeError):
    """Ошибка доставки email-сообщения."""


class EmailProviderNotImplementedError(EmailDeliveryError):
    """Провайдер email-доставки объявлен, но еще не реализован."""


__all__ = ["EmailDeliveryError", "EmailProviderNotImplementedError"]
