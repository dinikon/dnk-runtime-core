from typing import Protocol
from uuid import UUID
from src.modules.funnel.application.port.read_row import FunnelReadRowDTO


class FunnelQueryRepositoryProtocol(Protocol):
    """Контракт проекций, не восстанавливающий агрегат для UI."""

    async def get(self, funnel_id: UUID) -> FunnelReadRowDTO | None:
        """Читает определение процесса."""
        ...

    async def list(
        self, model_key: str | None, search: str, offset: int, limit: int
    ) -> tuple[tuple[FunnelReadRowDTO, ...], int]:
        """Читает страницу определений, default в начале выдачи."""
        ...
