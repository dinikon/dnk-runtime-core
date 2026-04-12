from enum import StrEnum


class TenantStatus(StrEnum):
    """Статусы жизненного цикла tenant."""

    ACTIVE = "active"
    FREEZE = "freeze"


class TenantDomainKind(StrEnum):
    """Тип происхождения tenant domain."""

    DEFAULT = "default"
    CUSTOM = "custom"


class TenantDomainStatus(StrEnum):
    """Статусы доступности tenant domain."""

    ACTIVE = "active"
    PENDING_VERIFICATION = "pending_verification"
    DISABLED = "disabled"
    DELETED = "deleted"


class TenantDomainTlsMode(StrEnum):
    """Режим управления TLS для tenant domain."""

    MANAGED = "managed"
    EXTERNAL = "external"


class TenantDomainVerificationStatus(StrEnum):
    """Статусы проверки владения tenant domain."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class TenantServiceType(StrEnum):
    """Типы сервисов, для которых может быть зарегистрирован tenant domain."""

    CONSOLE = "console"
    API = "http"
    SHORTLINKS = "shortlinks"


class TenantApiAuthMode(StrEnum):
    """Режимы авторизации API tenant domain."""

    TOKEN = "token"


__all__ = [
    "TenantApiAuthMode",
    "TenantDomainKind",
    "TenantDomainStatus",
    "TenantDomainTlsMode",
    "TenantDomainVerificationStatus",
    "TenantServiceType",
    "TenantStatus",
]
