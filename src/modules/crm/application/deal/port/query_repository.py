from typing import Protocol
from uuid import UUID
from src.modules.crm.application.deal.port.read_row import DealReadRowDTO


class DealQueryRepositoryProtocol(Protocol):
    """Чтение собственных проекций карточек и фильтрованной страницы."""

    async def get(self, record_id: UUID) -> DealReadRowDTO | None:
        """Читает карточку без восстановления агрегата."""
        ...

    async def list(
        self,
        *,
        funnel_id: UUID | None,
        stage_id: UUID | None,
        search: str,
        converted: bool | None,
        offset: int,
        limit: int,
        sort: str,
    ) -> tuple[tuple[DealReadRowDTO, ...], int]:
        """Возвращает страницу и полный счётчик соответствующего фильтра."""
        ...
