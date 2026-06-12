from typing import Protocol

from src.modules.broadcast.application.broadcast.dto import (
    BroadcastFieldsDescriptionDTO,
)
from src.modules.broadcast.application.broadcast.query import (
    BroadcastFieldsDescriptionRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class DescribeBroadcastFieldsUseCaseProtocol(Protocol):
    """Порт use case получения описания broadcast-модели."""

    async def __call__(self, tenant_id: EntityIdVO) -> BroadcastFieldsDescriptionDTO:
        """Возвращает описание broadcast и его полей для tenant."""
        ...


class DescribeBroadcastFieldsUseCase:
    """Use case чтения описания broadcast-модели."""

    def __init__(
        self,
        repository: BroadcastFieldsDescriptionRepositoryProtocol,
    ) -> None:
        """Инициализирует use case репозиторием описания broadcast."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> BroadcastFieldsDescriptionDTO:
        """Возвращает описание broadcast-объекта и его полей."""
        return await self._repository.describe_fields(tenant_id=tenant_id)


__all__ = [
    "DescribeBroadcastFieldsUseCase",
    "DescribeBroadcastFieldsUseCaseProtocol",
]
