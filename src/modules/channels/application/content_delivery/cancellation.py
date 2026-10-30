from src.modules.channels.domain.content_delivery.repository import (
    ContentDeliveryRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentDeliveryCancellation:
    """Отменяет ожидающие записи в том же UoW, что отключение representation."""

    def __init__(
        self, deliveries: ContentDeliveryRepositoryProtocol, clock: ClockPort
    ) -> None:
        """Принимает write-порт корня и общие часы, не открывает транзакцию."""
        self._deliveries, self._clock = deliveries, clock

    async def cancel(self, representation_id: EntityIdVO) -> None:
        """Начатые запросы сохраняются для фиксации результата или сверки."""
        for delivery in await self._deliveries.for_representation(representation_id):
            delivery.cancel(now=self._clock.now())
            await self._deliveries.save(delivery)
