from datetime import datetime
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_internal_move_creation_request import (
    StockInternalMoveCreationRequestModel as Request,
)
from src.modules.inventory.application.stock_document.port.internal_move_creation_requests import (
    InternalMoveCreationClaim,
)
from src.modules.inventory.application.stock_document.command.create_internal_move_draft.dto import (
    CreateInternalMoveDraftResultDTO,
)
from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_creation_mapper import (
    InternalMoveCreationResultMapper,
)


class SqlAlchemyInternalMoveCreationRequests:
    """Сериализует ключ создания в общей транзакции без локального rollback."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию внешнего UoW."""
        self._session = session

    async def claim(
        self, actor_id: UUID, key: str, fingerprint: str, created_at: datetime
    ) -> InternalMoveCreationClaim:
        """Конкурентный INSERT ожидает commit первой попытки либо её rollback."""
        statement = (
            pg_insert(Request)
            .values(
                actor_id=actor_id,
                idempotency_key=key,
                fingerprint=fingerprint,
                created_at=created_at,
            )
            .on_conflict_do_nothing(
                constraint="pk_stock_internal_move_creation_requests"
            )
            .returning(Request.actor_id)
        )
        created = await self._session.scalar(statement)
        if created is not None:
            return InternalMoveCreationClaim(True, fingerprint, None)
        statement_read = (
            select(Request)
            .where(Request.actor_id == actor_id, Request.idempotency_key == key)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement_read)).one()
        return InternalMoveCreationClaim(
            False,
            model.fingerprint,
            (
                InternalMoveCreationResultMapper.from_record(model.result)
                if model.result is not None
                else None
            ),
        )

    async def complete(
        self, actor_id: UUID, key: str, result: CreateInternalMoveDraftResultDTO
    ) -> None:
        """Фиксирует ответ вместе с новым документом, исключая перезапись готового результата."""
        statement = (
            update(Request)
            .where(
                Request.actor_id == actor_id,
                Request.idempotency_key == key,
                Request.document_id.is_(None),
            )
            .values(
                document_id=result.id,
                result=InternalMoveCreationResultMapper.to_record(result),
            )
            .returning(Request.actor_id)
        )
        if await self._session.scalar(statement) is None:
            raise RuntimeError("Запрос создания не захвачен или уже завершён.")
