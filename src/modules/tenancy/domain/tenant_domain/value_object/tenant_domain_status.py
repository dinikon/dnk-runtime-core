from enum import StrEnum


class TenantDomainStatus(StrEnum):
    """Статусы доступности tenant domain."""

    ACTIVE = "active"
    PENDING_VERIFICATION = "pending_verification"
    DISABLED = "disabled"
    DELETED = "deleted"


__all__ = ["TenantDomainStatus"]
