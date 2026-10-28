from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.channels.application.catalog_binding.contracts import (
    BindingRecord,
    CatalogFamilyDTO,
    BindingCandidatesDTO,
    PublicationNodeDTO,
    BindingConnectionDTO,
)
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingClaim,
    BindingMode,
)


class BindingCatalogPort(Protocol):
    """Изолирует публичные контракты владельца Catalog."""

    async def lock(self, tenant_id: UUID, root_id: UUID) -> None:
        """Блокирует источник в общем UoW."""
        ...

    async def families(
        self, ids: tuple[UUID, ...], locale: str, now: datetime
    ) -> tuple[CatalogFamilyDTO, ...]:
        """Читает семейные проекции batch."""
        ...

    async def search(
        self,
        tenant_id: UUID,
        mode: BindingMode,
        locale: str,
        search: str,
        offset: int,
        limit: int,
        now: datetime,
    ) -> BindingCandidatesDTO:
        """Возвращает подходящие корни до пагинации."""
        ...


class BindingReadPort(Protocol):
    """Читает локальные данные Channels без восстановления агрегатов."""

    async def connection(self, channel_id: UUID) -> BindingConnectionDTO | None:
        """Читает подключение без восстановления агрегата."""
        ...

    async def records(
        self,
        *,
        catalog_root_id: UUID | None = None,
        connection_id: UUID | None = None,
        group_id: UUID | None = None,
        publication_id: UUID | None = None,
        publication_ids: tuple[UUID, ...] = (),
        mode: BindingMode | None = None,
        offset: int = 0,
        limit: int | None = 25,
    ) -> tuple[tuple[BindingRecord, ...], int]:
        """Пагинирует группы, затем пакетно читает пары."""
        ...

    async def nodes(
        self, connection_id: UUID, ids: tuple[UUID, ...], locale: str
    ) -> tuple[PublicationNodeDTO, ...]:
        """Читает затронутые семьи без внешнего API."""
        ...

    async def claims(
        self, connection_id: UUID, ids: tuple[UUID, ...]
    ) -> tuple[BindingClaim, ...]:
        """Находит закрепления заголовков и позиций."""
        ...

    async def candidates(
        self,
        connection_id: UUID,
        platform: str,
        mode: BindingMode,
        locale: str,
        search: str,
        offset: int,
        limit: int,
    ) -> BindingCandidatesDTO:
        """Фильтрует структуру до пагинации."""
        ...

    async def used(
        self, catalog_root_id: UUID, position_id: UUID | None = None
    ) -> bool:
        """Проверяет использование для владельца Catalog."""
        ...
