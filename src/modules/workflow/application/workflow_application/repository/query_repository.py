from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.workflow.application.workflow_application import (
    WorkflowApplicationCursor,
)
from src.modules.workflow.application.workflow_application.dto import (
    WorkflowApplicationListItemDTO,
)


class WorkflowApplicationQueryRepositoryProtocol(Protocol):
    """Query repository port for workflow applications."""

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        cursor: WorkflowApplicationCursor | None,
    ) -> list[WorkflowApplicationListItemDTO]:
        """Returns workflow applications page ordered by cursor order."""
        ...


__all__ = ["WorkflowApplicationQueryRepositoryProtocol"]
