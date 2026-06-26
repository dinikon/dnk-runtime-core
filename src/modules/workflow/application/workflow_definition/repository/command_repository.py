from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.workflow.domain import WorkflowDefinitionEntity


class WorkflowDefinitionCommandRepositoryProtocol(Protocol):
    """Command repository port for workflow definitions."""

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        definition: WorkflowDefinitionEntity,
    ) -> WorkflowDefinitionEntity:
        """Persists workflow definition."""
        ...


__all__ = ["WorkflowDefinitionCommandRepositoryProtocol"]
