import re
from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class TenantSchemaNaming:
    """Единое неизменяемое правило имени tenant-схемы."""

    prefix: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z_][a-z0-9_]{3,9}", self.prefix):
            raise ValueError(
                "Tenant schema prefix must be 4–10 lowercase SQL identifier characters."
            )

    def schema_name(self, tenant_id: EntityIdVO) -> str:
        """Возвращает имя схемы из префикса и UUID tenant."""
        return f"{self.prefix}{tenant_id.uuid.hex}"
