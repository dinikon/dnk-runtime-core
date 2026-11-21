from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_internal_move_posting_requests import (
    InternalMovePostingRequestModel,
)
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.query import (
    GetInternalMoveExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.dto import (
    GetInternalMoveExecutionResultDTO,
)


class SqlAlchemyInternalMoveExecutionResultRepository:
    """Читает immutable JSON результата, не восстанавливая доменные агрегаты."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего tenant-UoW."""
        self._session = session

    async def get(
        self, query: GetInternalMoveExecutionResultQuery
    ) -> GetInternalMoveExecutionResultDTO | None:
        """Декодирует конкретный DTO собственного сценария с Decimal и UUID."""
        statement = (
            select(InternalMovePostingRequestModel)
            .where(InternalMovePostingRequestModel.execution_id == query.identifier)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        if model.result is None:
            raise RuntimeError(
                "Завершённое исполнение не содержит первоначального результата."
            )
        return TypeAdapter(GetInternalMoveExecutionResultDTO).validate_python(
            model.result
        )
