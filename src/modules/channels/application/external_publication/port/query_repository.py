"""Конкретные безопасные снимки для сборки карточек Console."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationKind,
)


@dataclass(frozen=True, slots=True)
class PublicationConnectionReadRow:
    """Публичный контекст подключения без ciphertext и verification payload."""

    id: UUID
    config_revision: int
    platform_kind: str
    config: ConnectionConfigVO


@dataclass(frozen=True, slots=True)
class PublicationReadRow:
    """Поддержанный снимок без тяжёлых исходных ответов и нативных секретов."""

    id: UUID
    external_id: str
    kind: PublicationKind
    parent_id: UUID | None
    data: PublicationData
    revision: int
    last_seen_at: datetime
    observed_config_revision: int


class PublicationQueryRepository(Protocol):
    """Читает карточки пакетно без восстановления агрегатов."""

    async def connection(self, channel_id: UUID) -> PublicationConnectionReadRow | None:
        """Находит контекст выбранного канала текущего tenant."""
        ...

    async def list_roots(
        self,
        connection_id: UUID,
        search: str,
        offset: int,
        limit: int,
        binding: str = "",
    ) -> tuple[tuple[PublicationReadRow, ...], int]:
        """Пагинирует по корням, включая совпадения поиска среди детей."""
        ...

    async def get(
        self, connection_id: UUID, publication_id: UUID
    ) -> PublicationReadRow | None:
        """Читает реальную публикацию в границах подключения."""
        ...

    async def children(
        self, connection_id: UUID, root_ids: tuple[UUID, ...]
    ) -> tuple[PublicationReadRow, ...]:
        """Загружает участников выбранных карточек одним запросом."""
        ...
