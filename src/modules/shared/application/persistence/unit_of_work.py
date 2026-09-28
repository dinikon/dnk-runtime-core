from typing import Protocol


class UnitOfWorkProtocol(Protocol):
    """Управление уже открытой транзакцией без инфраструктурных типов."""

    async def commit(self) -> None:
        """Фиксирует изменения процесса; ошибка передаётся вызывающей границе."""
        ...

    async def rollback(self) -> None:
        """Откатывает текущую транзакцию процесса."""
        ...
