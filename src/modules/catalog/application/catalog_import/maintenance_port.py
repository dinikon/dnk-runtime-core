from typing import Protocol
from uuid import UUID


class ImportMaintenancePort(Protocol):
    """Сверка заданий и очистка принадлежащих импорту технических данных."""

    async def job_terminal(self, job_id: UUID) -> bool:
        """Проверяет окончательное завершение или отсутствие связанного задания."""
        ...

    async def clear_source(
        self, identifier: UUID, file_id: UUID | None, actor_id: UUID
    ) -> None:
        """Снимает исходные payload и отправляет только source-файл в Files trash."""
        ...

    async def delete_results(self, identifier: UUID) -> None:
        """Удаляет истёкший журнал, не затрагивая файлы галерей."""
        ...
