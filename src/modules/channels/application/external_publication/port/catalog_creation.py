from typing import Protocol
from uuid import UUID
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationCreationSnapshot,
    PublicationDetails,
    CreatedPublicationCatalog,
)


class PublicationCreationReadPort(Protocol):
    """Читает локальный контекст без восстановления агрегатов."""

    async def snapshot(
        self, channel_id: UUID, publication_id: UUID
    ) -> PublicationCreationSnapshot:
        """Возвращает корень и все известные варианты его подключения."""
        ...


class PublicationCatalogPort(Protocol):
    """Изолирует подготовку и запись владельца Catalog."""

    async def lock(self, tenant_id: UUID, root_id: UUID) -> None:
        """Блокирует будущий корень перед Channel."""
        ...

    async def create(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        root_id: UUID,
        details: PublicationDetails,
        platform: str,
        images: dict[str, UUID],
    ) -> CreatedPublicationCatalog:
        """Создаёт Draft с полученными значениями в общей транзакции."""
        ...


class PublicationImagesPort(Protocol):
    """Загружает изображения до транзакции Catalog."""

    async def download(
        self, identifier: UUID, url: str
    ) -> tuple[UUID | None, str | None]:
        """Возвращает готовый File или безопасное предупреждение."""
        ...
