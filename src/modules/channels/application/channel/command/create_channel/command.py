from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateChannelCommand:
    """Передаёт параметры на создание канала с настройками, активностью и инициатором."""

    tenant_id: UUID
    actor_id: UUID
    name: str
    kind: str
    config_version: int
    connection_settings: dict[str, str] = field(repr=False)
    is_active: bool = True
