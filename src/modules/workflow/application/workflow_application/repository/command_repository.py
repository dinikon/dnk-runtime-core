from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowDefinitionEntity,
)


class WorkflowApplicationCommandRepositoryProtocol(Protocol):
    """Command repository port for workflow applications."""

    async def save_with_definition(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: WorkflowApplicationEntity,
        definition: WorkflowDefinitionEntity,
    ) -> tuple[WorkflowApplicationEntity, WorkflowDefinitionEntity]:
        """Persists workflow application and its initial draft definition."""
        ...


__all__ = ["WorkflowApplicationCommandRepositoryProtocol"]
