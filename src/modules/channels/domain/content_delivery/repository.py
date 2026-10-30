from typing import Protocol
from src.modules.channels.domain.content_delivery.aggregate import ContentDelivery
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentDeliveryRepositoryProtocol(Protocol):
    """Хранит агрегаты целей в текущем tenant UoW."""

    async def get(
        self, representation_id: EntityIdVO, publication_id: EntityIdVO
    ) -> ContentDelivery | None:
        """Загружает и блокирует цель перед изменением."""
        ...

    async def save(self, delivery: ContentDelivery) -> None:
        """Сохраняет агрегат без самостоятельного commit."""
        ...

    async def for_representation(
        self, representation_id: EntityIdVO
    ) -> tuple[ContentDelivery, ...]:
        """Блокирует цели для отмены ожидающих записей после отключения экспорта."""
        ...
