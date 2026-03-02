from enum import StrEnum


class TenantDomainTlsMode(StrEnum):
    MANAGED = "managed"
    EXTERNAL = "external"
