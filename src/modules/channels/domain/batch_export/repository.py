from typing import Protocol
from uuid import UUID
from src.modules.channels.domain.batch_export.aggregate import BatchExportRun
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO


class BatchExportRepository(Protocol):
    """Сохраняет корень вместе с ограниченными частями его неизменяемого снимка."""

    async def get(self, identifier: UUID) -> BatchExportRun:
        """Блокирует корень для перехода состояния."""
        ...

    async def find(self, identifier: UUID) -> BatchExportRun | None:
        """Находит ранее принятое намерение пользователя."""
        ...

    async def active(self, connection_id: UUID) -> BatchExportRun | None:
        """Возвращает единственный занятый слот подключения."""
        ...

    async def add(self, run: BatchExportRun) -> None:
        """Атомарно регистрирует корень и состав разрешённых активных связей."""
        ...

    async def save(
        self, run: BatchExportRun, items: tuple[ExportItemVO, ...] = ()
    ) -> None:
        """Сохраняет переход и результаты указанной части снимка без commit."""
        ...

    async def page(
        self, run_id: UUID, status: str, after: UUID | None = None, limit: int = 100
    ) -> tuple[ExportItemVO, ...]:
        """Читает ограниченную часть снимка для одного шага или потока XML."""
        ...

    async def matching(
        self, run_id: UUID, keys: tuple[str, ...], native_ids: tuple[str, ...]
    ) -> tuple[ExportItemVO, ...]:
        """Выбирает цели, затронутые страницей внешнего полного обхода."""
        ...

    async def counts(self, run_id: UUID) -> dict[str, int]:
        """Возвращает счётчики дочерних результатов для перехода корня."""
        ...

    async def current(self, run_id: UUID) -> bool:
        """Подтверждает актуальность всех зафиксированных связей и разрешений."""
        ...

    async def identities_valid(self, run_id: UUID) -> bool:
        """Требует единственного наблюдаемого владельца каждого ключа файла."""
        ...

    async def invalid_identities(self, run_id: UUID) -> tuple[ExportItemVO, ...]:
        """Читает до ста конфликтов полного внешнего обхода для исключения из файла."""
        ...

    async def reopen_verification(self, run_id: UUID) -> None:
        """Повторяет только чтение неопределённых результатов, не отправку."""
        ...
