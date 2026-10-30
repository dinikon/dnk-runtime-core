from src.modules.channels.application.content_delivery.query.get_content_deliveries.query import (
    GetContentDeliveriesQuery,
)
from src.modules.channels.application.content_delivery.query.get_content_deliveries.dto import (
    GetContentDeliveriesResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries


class GetContentDeliveriesHandler:
    """Читает безопасные проекции состояния целей."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Принимает координацию read-портов без инфраструктурных типов."""
        self._service = service

    async def execute(
        self, query: GetContentDeliveriesQuery
    ) -> GetContentDeliveriesResultDTO:
        """Не восстанавливает агрегаты только ради отображения."""
        return GetContentDeliveriesResultDTO(
            await self._service.read(
                tenant_id=query.tenant_id,
                channel_id=query.channel_id,
                group_id=query.group_id,
            )
        )
