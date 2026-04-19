from enum import StrEnum


class TenantApiAuthMode(StrEnum):
    """Режимы авторизации API tenant domain."""

    TOKEN = "token"


__all__ = ["TenantApiAuthMode"]
