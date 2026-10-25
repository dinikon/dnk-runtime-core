from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.funnel.domain.aggregate import Funnel


class FunnelRepositoryProtocol(Protocol):
    """Хранение определения процесса в общей сессии UoW."""

    async def get(
        self, funnel_id: EntityIdVO, *, for_update: bool = False
    ) -> Funnel | None:
        """Загружает определение для доменного решения."""
        ...

    async def get_default(self, model_key: str) -> Funnel | None:
        """Возвращает существующую default-воронку без bootstrap."""
        ...

    async def add(self, entity: Funnel) -> None:
        """Добавляет процесс без commit."""
        ...

    async def save(self, entity: Funnel) -> None:
        """Сохраняет процесс без commit."""
        ...
