from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class CleanupPriceListCommand:
    """Авторизованный запуск обслуживания staging одного tenant."""

    tenant_id: EntityIdVO
    job_id: EntityIdVO
    lock_token: str


__all__ = ["CleanupPriceListCommand"]
