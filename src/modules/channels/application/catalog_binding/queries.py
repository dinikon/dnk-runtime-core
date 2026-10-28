from datetime import datetime
from uuid import UUID
from src.modules.channels.application.catalog_binding.contracts import (
    BindingPairDTO,
    BindingPreviewDTO,
    BindingGroupDTO,
    BindingCandidatesDTO,
    BindingConnectionDTO,
)
from src.modules.channels.application.catalog_binding.ports import (
    BindingCatalogPort,
    BindingReadPort,
)
from src.modules.channels.application.catalog_binding.views import BindingViews
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError


class BindingQueries:
    """Read-координация локальных сценариев без записи и сетевого API площадки."""

    def __init__(
        self, read: BindingReadPort, catalog: BindingCatalogPort, views: BindingViews
    ) -> None:
        """Использует порты одной tenant-сессии."""
        self.read, self.catalog, self.views = read, catalog, views

    async def connection(self, channel_id: UUID) -> BindingConnectionDTO:
        """Не раскрывает наличие чужого подключения."""
        value = await self.read.connection(channel_id)
        if value is None:
            raise CatalogBindingError("channel_not_found")
        return value

    @staticmethod
    def pagination(offset: int, limit: int) -> None:
        """Ограничивает размер страниц и неотрицательный offset."""
        if offset < 0 or not 1 <= limit <= 100:
            raise CatalogBindingError("pagination_invalid")

    async def get(
        self, channel_id: UUID, group_id: UUID, locale: str, now: datetime
    ) -> BindingGroupDTO:
        """Читает группу и вычисляет текущее состояние по владельцам."""
        connection = await self.connection(channel_id)
        records, _ = await self.read.records(
            connection_id=connection.id, group_id=group_id
        )
        if not records:
            raise CatalogBindingError("binding_not_found")
        return (await self.views.groups(records, locale, now))[0]

    async def list(
        self,
        *,
        catalog_root_id: UUID | None,
        channel_id: UUID | None,
        publication_id: UUID | None,
        offset: int,
        limit: int,
        locale: str,
        now: datetime,
        mode: BindingMode | None = None,
    ) -> tuple[tuple[BindingGroupDTO, ...], int]:
        """Пагинирует группы одного Catalog или подключения до batch-сборки."""
        self.pagination(offset, limit)
        if catalog_root_id is None and channel_id is None:
            raise CatalogBindingError("binding_scope_required")
        connection = await self.connection(channel_id) if channel_id else None
        records, total = await self.read.records(
            catalog_root_id=catalog_root_id,
            mode=mode,
            connection_id=connection.id if connection else None,
            publication_id=publication_id,
            offset=offset,
            limit=limit,
        )
        return await self.views.groups(records, locale, now), total

    async def preview(
        self,
        *,
        channel_id: UUID,
        catalog_root_id: UUID,
        mode: BindingMode,
        publication_root_id: UUID | None,
        items: tuple[BindingPairDTO, ...],
        locale: str,
        now: datetime,
        group_id: UUID | None = None,
    ) -> BindingPreviewDTO:
        """Проверяет immutable-якоря существующей группы и предлагаемое сопоставление."""
        connection = await self.connection(channel_id)
        if group_id:
            records, _ = await self.read.records(
                connection_id=connection.id, group_id=group_id
            )
            if not records:
                raise CatalogBindingError("binding_not_found")
            record = records[0]
            if (record.catalog_root_id, record.mode, record.publication_root_id) != (
                catalog_root_id,
                mode,
                publication_root_id,
            ):
                raise CatalogBindingError("binding_anchors_immutable")
        return await self.views.preview(
            connection_id=connection.id,
            platform=connection.platform,
            catalog_root_id=catalog_root_id,
            mode=mode,
            publication_root_id=publication_root_id,
            items=items,
            locale=locale,
            now=now,
            group_id=group_id,
        )

    async def catalog_candidates(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        mode: BindingMode,
        locale: str,
        search: str,
        offset: int,
        limit: int,
        now: datetime,
    ) -> BindingCandidatesDTO:
        """Ищет Catalog через публичный порт владельца."""
        self.pagination(offset, limit)
        await self.connection(channel_id)
        return await self.catalog.search(
            tenant_id, mode, locale, search, offset, limit, now
        )

    async def publication_candidates(
        self,
        *,
        channel_id: UUID,
        mode: BindingMode,
        locale: str,
        search: str,
        offset: int,
        limit: int,
    ) -> BindingCandidatesDTO:
        """Возвращает локальные корни площадки и признак занятости."""
        self.pagination(offset, limit)
        connection = await self.connection(channel_id)
        return await self.read.candidates(
            connection.id, connection.platform, mode, locale, search, offset, limit
        )
