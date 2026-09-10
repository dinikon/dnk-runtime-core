from enum import StrEnum


class TenantDomainVerificationStatus(StrEnum):
    """Статусы проверки владения tenant domain."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


__all__ = ["TenantDomainVerificationStatus"]
