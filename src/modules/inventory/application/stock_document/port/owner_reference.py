from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StockOwnerReference:
    """Публичная компания-владелец без агрегата CRM."""

    id: UUID
    name: str


class StockOwnerReferencePort(Protocol):
    """Проверяет и читает только компании CRM в явном пространстве идентификаторов."""

    async def get(
        self, identifier: UUID, *, lock: bool = False
    ) -> StockOwnerReference | None:
        """Проверяет выбранную компанию с защитой от удаления."""
        ...

    async def get_many(
        self, identifiers: tuple[UUID, ...]
    ) -> dict[UUID, StockOwnerReference]:
        """Читает имена владельцев пакетом без N+1."""
        ...
