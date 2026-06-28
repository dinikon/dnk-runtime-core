from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.workflow.application.workflow_application import (
    WorkflowApplicationQueryRepositoryProtocol,
)
from src.modules.workflow.application.workflow_application.dto import (
    WorkflowApplicationListDTO,
)
from src.modules.workflow.application.workflow_application.query import (
    ListWorkflowsQuery,
    WorkflowApplicationCursor,
)


class ListWorkflowsUseCaseProtocol(Protocol):
    """Use case port for listing workflow applications."""

    async def __call__(self, query: ListWorkflowsQuery) -> WorkflowApplicationListDTO:
        """Returns workflow applications page for tenant."""
        ...


class ListWorkflowsUseCase:
    """Lists workflow applications with cursor pagination."""

    def __init__(
        self,
        *,
        repository: WorkflowApplicationQueryRepositoryProtocol,
    ) -> None:
        self._repository = repository

    async def __call__(self, query: ListWorkflowsQuery) -> WorkflowApplicationListDTO:
        if query.limit < 1:
            raise ValueError("Workflow list limit must be >= 1.")
        if query.limit > 100:
            raise ValueError("Workflow list limit must be <= 100.")

        cursor = (
            None
            if query.cursor is None
            else WorkflowApplicationCursor.decode(query.cursor)
        )
        rows = await self._repository.list(
            tenant_id=EntityIdVO.from_value(query.tenant_id),
            limit=query.limit + 1,
            cursor=cursor,
        )
        items = tuple(rows[: query.limit])
        next_cursor = None
        if len(rows) > query.limit and items:
            last_item = items[-1]
            next_cursor = WorkflowApplicationCursor(
                created_at=last_item.created_at,
                id=last_item.id,
            ).encode()
        return WorkflowApplicationListDTO(
            items=items,
            next_cursor=next_cursor,
        )


__all__ = [
    "ListWorkflowsUseCase",
    "ListWorkflowsUseCaseProtocol",
]
