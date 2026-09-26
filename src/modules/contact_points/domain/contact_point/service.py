from collections.abc import Mapping
from src.modules.contact_points.domain.contact_point.entity import ContactPoint
from src.modules.contact_points.domain.contact_point.repository import (
    ContactPointRepositoryProtocol,
)
from src.modules.contact_points.domain.contact_point.normalization import (
    ContactPointNormalizerProtocol,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
    NormalizationContext,
)
from src.modules.shared.domain.time import ClockPort


class ContactPointResolver:
    """Разрешает канонический адрес без самостоятельного commit."""

    def __init__(
        self,
        repository: ContactPointRepositoryProtocol,
        normalizers: Mapping[ContactPointType, ContactPointNormalizerProtocol],
        clock: ClockPort,
    ):
        self.repository, self.normalizers, self.clock = repository, normalizers, clock

    def normalize(self, point_type, value, country_code):
        """Валидирует значение через стратегию его типа."""
        return self.normalizers[point_type].normalize(
            value, NormalizationContext(country_code)
        )

    async def resolve(self, tenant_id, actor_id, point_id, point_type, normalized):
        """Создаёт либо переиспользует точку в текущей транзакции."""
        return await self.repository.get_or_create(
            tenant_id,
            ContactPoint.create(
                point_id=point_id,
                point_type=point_type,
                normalized=normalized,
                actor_id=actor_id,
                now=self.clock.now(),
            ),
        )


__all__ = ["ContactPointResolver"]
