from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_status_change_posting_requests import (
    StatusChangePostingRequestModel,
)
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.query import (
    GetStatusChangeExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.dto import (
    GetStatusChangeExecutionResultDTO,
)


class SqlAlchemyStatusChangeExecutionResultRepository:
    """Читает immutable JSON результата, не восстанавливая доменные агрегаты."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего tenant-UoW."""
        self._session = session

    async def get(
        self, query: GetStatusChangeExecutionResultQuery
    ) -> GetStatusChangeExecutionResultDTO | None:
        """Декодирует конкретный DTO собственного сценария с Decimal и UUID."""
        statement = (
            select(StatusChangePostingRequestModel)
            .where(StatusChangePostingRequestModel.execution_id == query.identifier)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        if model.result is None:
            raise RuntimeError(
                "Завершённое исполнение не содержит первоначального результата."
            )
        return TypeAdapter(GetStatusChangeExecutionResultDTO).validate_python(
            model.result
        )
