from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPlatformConfigQuery:
    """Задаёт параметры чтения get_platform_config в доверенном tenant."""

    tenant_id: UUID
    platform_kind: str
