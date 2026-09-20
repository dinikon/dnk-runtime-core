from contextlib import asynccontextmanager
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork


class SqlAlchemyImportTransactionFactory:
    """Открывает shared UoW, компоненты собирает presentation factory."""

    def __init__(self, session_factory, assemble):
        self.session_factory = session_factory
        self.assemble = assemble

    @asynccontextmanager
    async def __call__(self):
        """Выполняет сценарий через внедрённые доменные порты."""
        async with UnitOfWork(self.session_factory) as uow:
            yield self.assemble(uow)


__all__ = ["SqlAlchemyImportTransactionFactory"]
