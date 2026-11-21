from src.modules.inventory.application.stock_document.query.list_receipt_references.query import (
    ListReceiptReferencesQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_references.dto import (
    ListReceiptReferencesResultDTO,
)
from src.modules.inventory.application.stock_document.query.prepare_receipt.query import (
    PrepareReceiptQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_receipt.dto import (
    PrepareReceiptResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.query import (
    ListReceiptExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.dto import (
    ListReceiptExecutionsResultDTO,
)
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_receipt.dto import (
    PostReceiptResultDTO,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution.dto import (
    GetStockExecutionResultDTO,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting.dto import (
    GetStockPostingResultDTO,
)


@dataclass(frozen=True, slots=True)
class ReceiptCommandClaim:
    """Возвращает новый захват либо ранее завершённый результат команды."""

    is_new: bool
    fingerprint: str
    result: PostReceiptResultDTO | None


class ReceiptPostingRequestsPort(Protocol):
    """Сериализует ключ сценария в tenant независимо от повторно обратившегося actor."""

    async def claim(
        self, key: str, fingerprint: str, actor_id: UUID, created_at: datetime
    ) -> ReceiptCommandClaim:
        """Захватывает ключ до проверки текущей версии и справочников."""
        ...

    async def complete(self, key: str, result: PostReceiptResultDTO) -> None:
        """Записывает неизменяемый исходный результат до общего commit."""
        ...

    async def add_links(self, links: tuple[tuple[UUID, UUID], ...]) -> None:
        """Сохраняет доказанное Domain соответствие фактических строк и Ledger."""
        ...


class ReceiptCurrencyPort(Protocol):
    """Проверяет известность валют через публичный контракт Reference Data."""

    async def ensure_codes(self, codes: tuple[str, ...]) -> None:
        """Отклоняет неизвестную либо неактивную валюту нового основания."""
        ...


class ReceiptFactsQueryPort(Protocol):
    """Читает сохранённые результаты без восстановления агрегатов."""

    async def get_execution(
        self, identifier: UUID
    ) -> GetStockExecutionResultDTO | None:
        """Возвращает конкретную карточку исполнения."""
        ...

    async def get_posting(self, identifier: UUID) -> GetStockPostingResultDTO | None:
        """Возвращает конкретную карточку проводки и Ledger."""
        ...

    async def list_executions(
        self, query: ListReceiptExecutionsQuery
    ) -> ListReceiptExecutionsResultDTO | None:
        """Отличает отсутствующий документ от пустой истории."""
        ...

    async def prepare(
        self, query: PrepareReceiptQuery
    ) -> PrepareReceiptResultDTO | None:
        """Читает оставшийся план, не загружая агрегат для UI."""
        ...

    async def references(
        self, query: ListReceiptReferencesQuery
    ) -> ListReceiptReferencesResultDTO | None:
        """Читает собственную проекцию выбора локации, партии или свободного экземпляра."""
        ...
