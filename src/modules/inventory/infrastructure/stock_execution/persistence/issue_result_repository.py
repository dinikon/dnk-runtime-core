from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_issue_posting_requests import (
    IssuePostingRequestModel,
)
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.query import (
    GetIssueExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.dto import (
    GetIssueExecutionResultDTO,
)


class SqlAlchemyIssueExecutionResultRepository:
    """Читает immutable JSON результата, не восстанавливая доменные агрегаты."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего tenant-UoW."""
        self._session = session

    async def get(
        self, query: GetIssueExecutionResultQuery
    ) -> GetIssueExecutionResultDTO | None:
        """Декодирует конкретный DTO собственного сценария с Decimal и UUID."""
        statement = (
            select(IssuePostingRequestModel)
            .where(IssuePostingRequestModel.execution_id == query.identifier)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        if model.result is None:
            raise RuntimeError(
                "Завершённое исполнение не содержит первоначального результата."
            )
        return TypeAdapter(GetIssueExecutionResultDTO).validate_python(model.result)
