from contextlib import asynccontextmanager
from dataclasses import dataclass
from src.modules.currency.infrastructure.persistence.resolution_failure.repository import (
    SqlResolutionFailureRepository,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork


@dataclass(slots=True)
class SqlFailureAuditTransaction:
    """Public sql failure audit transaction contract."""

    failures: SqlResolutionFailureRepository
    outbox: SqlAlchemyOutboxRepository


class SqlFailureAuditTransactions:
    """Use a separate shared UoW; its repositories never commit independently."""

    def __init__(self, session_factory, naming):
        self.session_factory, self.naming = session_factory, naming

    @asynccontextmanager
    async def __call__(self):
        async with UnitOfWork(self.session_factory) as uow:
            yield SqlFailureAuditTransaction(
                SqlResolutionFailureRepository(uow.session, self.naming),
                SqlAlchemyOutboxRepository(uow.session),
            )


__all__ = ["SqlFailureAuditTransactions"]
