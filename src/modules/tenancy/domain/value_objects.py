from enum import StrEnum


class TenantStatus(StrEnum):
    ACTIVE = "active"
    FREEZE = "freeze"


class TenantDomainKind(StrEnum):
    DEFAULT = "default"
    CUSTOM = "custom"


class TenantDomainStatus(StrEnum):
    ACTIVE = "active"
    PENDING_VERIFICATION = "pending_verification"
    DISABLED = "disabled"
    DELETED = "deleted"


class TenantDomainTlsMode(StrEnum):
    MANAGED = "managed"
    EXTERNAL = "external"


class TenantDomainVerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class TenantServiceType(StrEnum):
    CONSOLE = "console"
    API = "http"
    SHORTLINKS = "shortlinks"


class TenantApiAuthMode(StrEnum):
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
