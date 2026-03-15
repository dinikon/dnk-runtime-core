from enum import StrEnum


class TenantDomainVerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
