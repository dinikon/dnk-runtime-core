from enum import StrEnum


class TenantServiceType(StrEnum):
    """Типы сервисов, для которых может быть зарегистрирован tenant domain."""

    CONSOLE = "console"
    API = "http"
    SHORTLINKS = "shortlinks"


__all__ = ["TenantServiceType"]
