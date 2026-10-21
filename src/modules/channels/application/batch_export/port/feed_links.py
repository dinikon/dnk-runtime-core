from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ExportFeedAvailabilityDTO:
    """Различает локальную подготовку и доступность фида для внешнего источника."""

    feed_available: bool
    delivery_configured: bool


class BatchExportFeedLinks(Protocol):
    """Формирует адреса по зарегистрированным доменам tenant без зависимости от Request."""

    async def availability(self, tenant_id: UUID) -> ExportFeedAvailabilityDTO:
        """Проверяет возможность подготовки и автоматической передачи ссылки."""
        ...

    async def url(self, tenant_id: UUID, run_id: UUID, expires_at: datetime) -> str:
        """Возвращает подписанный адрес одного неизменяемого XML на домене tenant."""
        ...
