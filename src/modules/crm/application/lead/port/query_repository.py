from typing import Protocol
from uuid import UUID
from src.modules.crm.application.lead.port.read_row import LeadReadRowDTO


class LeadQueryRepositoryProtocol(Protocol):
    """Чтение собственных проекций карточек и фильтрованной страницы."""

    async def get(self, record_id: UUID) -> LeadReadRowDTO | None:
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
    ) -> tuple[tuple[LeadReadRowDTO, ...], int]:
        """Возвращает страницу и полный счётчик соответствующего фильтра."""
        ...
