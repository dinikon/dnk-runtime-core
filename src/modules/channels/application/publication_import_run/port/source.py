from dataclasses import dataclass, field
from typing import Protocol
from src.modules.channels.domain.external_publication.value_object.read_document import (
    PublicationReadDocumentVO,
)


@dataclass(frozen=True, slots=True)
class PublicationSourceConnection:
    """Передаёт адаптеру минимальные параметры подключения без логирования секретов."""

    kind: str
    public: dict[str, str]
    secrets: dict[str, str] = field(repr=False)


@dataclass(frozen=True, slots=True)
class PublicationSourceResource:
    """Передаёт один внешний ресурс после нормализации адаптером."""

    resource_type: str
    external_id: str
    parent_external_id: str | None
    raw_payload: str = field(repr=False)
    document: PublicationReadDocumentVO


@dataclass(frozen=True, slots=True)
class PublicationSourcePage:
    """Передаёт ограниченную страницу и устойчивый курсор продолжения."""

    resources: tuple[PublicationSourceResource, ...]
    next_checkpoint: str | None


class PublicationSourcePort(Protocol):
    """Получает страницы вне открытой бизнес-транзакции."""

    async def read_page(
        self, connection: PublicationSourceConnection, checkpoint: str
    ) -> PublicationSourcePage:
        """Читает страницу платформы и явно обозначает конец обхода."""
        ...
