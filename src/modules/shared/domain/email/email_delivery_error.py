from __future__ import annotations


class EmailDeliveryError(RuntimeError):
    """Ошибка доставки email-сообщения."""


__all__ = ["EmailDeliveryError"]
