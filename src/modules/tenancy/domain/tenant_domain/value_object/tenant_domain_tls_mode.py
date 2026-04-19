from enum import StrEnum


class TenantDomainTlsMode(StrEnum):
    """Режим управления TLS для tenant domain."""

    MANAGED = "managed"
    EXTERNAL = "external"


__all__ = ["TenantDomainTlsMode"]
