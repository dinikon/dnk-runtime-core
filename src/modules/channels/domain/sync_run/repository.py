from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.sync_run.aggregate import SyncRun


class SyncRunRepositoryProtocol(Protocol):
    """Хранит агрегаты первичной загрузки под блокировкой Channel."""

    async def channel_id(self, identifier: EntityIdVO) -> EntityIdVO:
        """Разрешает ID владельца до получения блокировки run."""
        ...

    async def get(self, identifier: EntityIdVO) -> SyncRun:
        """Загружает и блокирует run."""
        ...

    async def latest(self, connection_id: EntityIdVO) -> SyncRun | None:
        """Возвращает последний run подключения."""
        ...

    async def by_request(
        self, connection_id: EntityIdVO, request_key: EntityIdVO
    ) -> SyncRun | None:
        """Находит идемпотентный запрос до проверки нового состояния."""
        ...

    async def add(self, run: SyncRun) -> None:
        """Добавляет run без commit."""
        ...

    async def save(self, run: SyncRun) -> None:
        """Сохраняет run без commit."""
        ...
