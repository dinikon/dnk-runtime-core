from enum import StrEnum


class TenantDomainKind(StrEnum):
    """Тип происхождения tenant domain."""

    DEFAULT = "default"
    CUSTOM = "custom"


__all__ = ["TenantDomainKind"]
