from enum import StrEnum


class TenantStatus(StrEnum):
    """Статусы жизненного цикла tenant."""

    ACTIVE = "active"
    FREEZE = "freeze"
    PROVISIONING = "provisioning"
    DELETION_PENDING = "deletion_pending"
    BLOCKED = "blocked"
    PURGING = "purging"


__all__ = ["TenantStatus"]
