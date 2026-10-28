"""Контракт сохранения самостоятельного агрегата синхронизации."""

from typing import Protocol

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.sync_run.aggregate import SyncRun


class SyncRunRepositoryProtocol(Protocol):
    """Работает на транзакции, общей с Channel и публикациями."""

    async def get(self, run_id: EntityIdVO) -> SyncRun | None:
        """Восстанавливает запуск либо возвращает отсутствие."""
        ...

    async def active(self, connection_id: EntityIdVO) -> SyncRun | None:
        """Находит активный запуск под блокировкой Channel."""
        ...

    async def automatic_exists(
        self, connection_id: EntityIdVO, config_revision: int
    ) -> bool:
        """Проверяет, был ли уже создан автоматический запуск ревизии."""
        ...

    async def save(self, run: SyncRun) -> None:
        """Сохраняет запуск без самостоятельного commit."""
        ...
