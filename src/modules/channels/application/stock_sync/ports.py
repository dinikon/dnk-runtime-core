from src.modules.channels.domain.stock_sync.state import DesiredStockVO
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
)
from src.modules.channels.domain.stock_sync.aggregate import StockSync
from src.modules.channels.domain.stock_sync.value_object import StockSnapshotVO
from src.modules.channels.domain.types import JsonObject


@dataclass(frozen=True, slots=True)
class StockPublication:
    """Снимок обращения к API и сведения о локальном владельце остатка."""

    lookup: PublicationLookup
    stock_mode: str
    quantity: str | None
    availability: str | None
    write_target_key: str | None = None


@dataclass(frozen=True, slots=True)
class StockSyncRow:
    """Проекция состояния без восстановления агрегата ради отображения."""

    publication_id: UUID
    operation_id: UUID
    direction: str
    status: str
    quantity: str | None
    availability: str | None
    observed_at: datetime | None
    desired_state: DesiredStockVO | None
    error_code: str | None
    updated_at: datetime
    recovery_required: bool = False


class StockReadPort(Protocol):
    """Чтение локального контекста Channels без доступа к Catalog SQL."""

    async def publications(
        self, connection_id: UUID, ids: tuple[UUID, ...]
    ) -> tuple[StockPublication, ...]:
        """Возвращает запрошенные позиции, родителей и детей затронутых семей."""
        ...

    async def states(
        self, connection_id: UUID, publication_ids: tuple[UUID, ...]
    ) -> tuple[StockSyncRow, ...]:
        """Читает текущие результаты выбранных физических остатков."""
        ...


class StockJobsPort(Protocol):
    """Shared Jobs хранит только идентификаторы операции."""

    async def schedule(
        self, *, tenant_id: UUID, channel_id: UUID, state: StockSync, now: datetime
    ) -> None:
        """Регистрирует одно поколение задания в текущем UoW."""
        ...

    async def cancel_channel(
        self, *, tenant_id: UUID, channel_id: UUID, now: datetime
    ) -> None:
        """Отменяет задания удаляемого подключения."""
        ...

    async def active(self, *, tenant_id: UUID, job_id: UUID) -> bool:
        """Проверяет потерянное или окончательно завершённое задание."""
        ...

    async def owns(
        self,
        *,
        tenant_id: UUID,
        job_id: UUID,
        lock_token: str,
        for_update: bool = False,
    ) -> bool:
        """Проверяет lease перед применением ответа."""
        ...


class StockPublicationWriter(Protocol):
    """Применение узкого наблюдения через доменный метод публикации."""

    async def apply(
        self,
        *,
        connection_id: UUID,
        publication_id: UUID,
        owner_id: UUID,
        stock: StockSnapshotVO,
        platform_data: JsonObject,
        now: datetime,
        config_revision: int,
    ) -> None:
        """Меняет только остаток, не трогая Catalog, контент и полный raw снимок."""
        ...
