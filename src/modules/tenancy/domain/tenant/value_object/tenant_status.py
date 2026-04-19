from enum import StrEnum


class TenantStatus(StrEnum):
    """Статусы жизненного цикла tenant."""

    ACTIVE = "active"
    FREEZE = "freeze"


__all__ = ["TenantStatus"]
