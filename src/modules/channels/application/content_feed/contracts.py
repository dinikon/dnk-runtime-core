from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.modules.channels.domain.product_representation.value_object import (
    PreparedPublicationContent,
)
from src.modules.channels.domain.types import JsonObject

MAX_FEED_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class FeedReadRow:
    """Проекция настроек без восстановления агрегата для списка и карточки."""

    id: UUID
    revision: int
    enabled: bool
    scope_key: str
    source_schema: str
    source_settings: JsonObject
    token_encrypted: bytes | None = field(repr=False)
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FeedDetails:
    """Публичные поля управления; исходный URL и plaintext токен отдельно не выдаются."""

    id: UUID
    revision: int
    enabled: bool
    scope_key: str
    source_schema: str
    source_settings: JsonObject
    public_url: str | None = field(repr=False)
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FeedPublicationKey:
    """Подтверждённый ключ обмена публикации с ревизией наблюдения."""

    publication_id: UUID
    revision: int
    import_key: str | None


@dataclass(frozen=True, slots=True)
class FeedGroupSnapshot:
    """Согласованный контент разрешённой группы без времени вычисления."""

    group_id: UUID
    revision: int
    binding_revision: int
    config_revision: int
    targets: tuple[PreparedPublicationContent, ...]


@dataclass(frozen=True, slots=True)
class FeedSnapshot:
    """Вектор контекста для проверки после сетевых операций и перед ответом."""

    connection_id: UUID
    channel_revision: int
    groups: tuple[FeedGroupSnapshot, ...]
    publications: tuple[FeedPublicationKey, ...]


@dataclass(frozen=True, slots=True)
class FeedOverlay:
    """Разрешённый контент одной исходной позиции; URLs доступны только serializer."""

    publication_id: UUID
    import_key: str
    target: PreparedPublicationContent
    gallery: tuple[str, ...] | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class FeedStatistics:
    """Счётчики полностью проверенного документа."""

    offers: int
    changed_offers: int
    categories: int


@dataclass(frozen=True, slots=True)
class RenderedFeed:
    """Готовые проверенные байты; HTTP не начинает ответ в процессе сборки."""

    content: bytes = field(repr=False)
    statistics: FeedStatistics
