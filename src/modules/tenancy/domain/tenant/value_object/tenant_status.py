from enum import StrEnum


class TenantStatus(StrEnum):
    """Статусы жизненного цикла tenant."""

    ACTIVE = "active"
    FREEZE = "freeze"
    PROVISIONING = "provisioning"


__all__ = ["TenantStatus"]
