from datetime import datetime
from uuid import UUID
from sqlalchemy import select, update, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.application.stock_document.port.return_posting import (
    ReturnCommandClaim,
)
from src.modules.inventory.application.stock_document.command.post_return.dto import (
    PostReturnResultDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_return_posting_requests import (
    ReturnPostingRequestModel as Model,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_ledger_links import (
    StockExecutionLedgerLinkModel as Link,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_record_mapper import (
    ReturnPostingRecordMapper,
)


class SqlAlchemyReturnPostingRequests:
    """Сериализует ключ в tenant и фиксирует результат без независимой транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию внешнего UoW."""
        self._session = session

    async def claim(
        self, key: str, fingerprint: str, actor_id: UUID, created_at: datetime
    ) -> ReturnCommandClaim:
        """INSERT ожидает чужой commit либо становится новым победителем после rollback."""
        statement = (
            pg_insert(Model)
            .values(
                key=key,
                fingerprint=fingerprint,
                actor_id=actor_id,
                created_at=created_at,
            )
            .on_conflict_do_nothing(constraint="pk_stock_return_posting_requests")
            .returning(Model.key)
        )
        if await self._session.scalar(statement) is not None:
            return ReturnCommandClaim(True, fingerprint, None)
        statement_read = (
            select(Model)
            .where(Model.key == key)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement_read)).one()
        return ReturnCommandClaim(
            False,
            model.fingerprint,
            (
                ReturnPostingRecordMapper.to_command(model.result)
                if model.result is not None
                else None
            ),
        )

    async def complete(self, key: str, result: PostReturnResultDTO) -> None:
        """Сохраняет первоначальный ответ только в незавершённый захваченный ключ."""
        statement = (
            update(Model)
            .where(Model.key == key, Model.execution_id.is_(None))
            .values(
                execution_id=result.execution_id,
                posting_id=result.posting_id,
                result=ReturnPostingRecordMapper.to_record(result),
            )
            .returning(Model.key)
        )
        if await self._session.scalar(statement) is None:
            raise RuntimeError("Ключ возврата уже завершён либо не захвачен.")

    async def add_links(self, links: tuple[tuple[UUID, UUID, str], ...]) -> None:
        """Вставляет неизменяемую детализацию агрегированных записей Ledger."""
        if links:
            await self._session.execute(
                insert(Link),
                [
                    dict(
                        execution_line_id=line,
                        ledger_entry_id=entry,
                        role=role,
                    )
                    for line, entry, role in links
                ],
            )
