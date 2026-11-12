from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FindInventoryItemUsageResultDTO:
    """Сообщает о связи независимо от роли и статуса карточки."""

    in_use: bool
