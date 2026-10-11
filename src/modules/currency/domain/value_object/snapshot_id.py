from typing import Self
import uuid6
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ExchangeRateSnapshotIdVO(EntityIdVO):
    """Идентифицирует состав и дату согласованного снимка котировок."""

    @classmethod
    def generate(cls) -> Self:
        """Создаёт UUIDv7 нового снимка."""
        return cls(uuid6.uuid7())
