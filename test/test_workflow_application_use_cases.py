from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.shared import EntityIdVO
from src.modules.workflow.application.workflow_application import (
    CreateWorkflowCommand,
    CreateWorkflowUseCase,
)
from src.modules.workflow.domain import (
    WorkflowApplicationIdVO,
    WorkflowApplicationStatusVO,
    WorkflowDefinitionIdVO,
    WorkflowKindVO,
)


class _UuidGeneratorStub:
    def __init__(self, *values: UUID) -> None:
        self._values = list(values)

    def new(self) -> UUID:
        return self._values.pop(0)


class _ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _WorkflowApplicationRepositoryStub:
    def __init__(self) -> None:
        self.saved_tenant_id = None
        self.saved_workflow = None

    async def save(self, *, tenant_id, workflow):
        self.saved_tenant_id = tenant_id
        self.saved_workflow = workflow
        return workflow


class _WorkflowDefinitionRepositoryStub:
    def __init__(self) -> None:
        self.saved_tenant_id = None
        self.saved_definition = None

    async def save(self, *, tenant_id, definition):
        self.saved_tenant_id = tenant_id
        self.saved_definition = definition
        return definition


class WorkflowApplicationUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_workflow_saves_default_workflow_with_empty_draft(
        self,
    ) -> None:
        tenant_id = uuid4()
        created_by = uuid4()
        workflow_id = uuid4()
        definition_id = uuid4()
        now = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
        application_repository = _WorkflowApplicationRepositoryStub()
        definition_repository = _WorkflowDefinitionRepositoryStub()
        use_case = CreateWorkflowUseCase(
            application_repository=application_repository,
            definition_repository=definition_repository,
            clock=_ClockStub(now),
            uuid_generator=_UuidGeneratorStub(workflow_id, definition_id),
        )

        result = await use_case(
            CreateWorkflowCommand(
                tenant_id=tenant_id,
                created_by=created_by,
                title="  Customer journey  ",
                description="Default customer workflow",
                icon="  workflow  ",
                icon_background="  #ffffff  ",
            )
        )

        self.assertEqual(
            application_repository.saved_tenant_id,
            EntityIdVO.from_value(tenant_id),
        )
        self.assertEqual(
            definition_repository.saved_tenant_id,
            EntityIdVO.from_value(tenant_id),
        )
        self.assertIsNotNone(application_repository.saved_workflow)
        self.assertIsNotNone(definition_repository.saved_definition)
        assert application_repository.saved_workflow is not None
        assert definition_repository.saved_definition is not None

        workflow = application_repository.saved_workflow
        definition = definition_repository.saved_definition

        self.assertEqual(workflow.id, WorkflowApplicationIdVO.from_value(workflow_id))
        self.assertEqual(
            definition.id,
            WorkflowDefinitionIdVO.from_value(definition_id),
        )
        self.assertEqual(workflow.created_at, now)
        self.assertEqual(workflow.updated_at, now)
        self.assertEqual(workflow.created_by, EntityIdVO.from_value(created_by))
        self.assertEqual(workflow.updated_by, EntityIdVO.from_value(created_by))
        self.assertEqual(workflow.kind, WorkflowKindVO.STANDARD)
        self.assertEqual(workflow.status, WorkflowApplicationStatusVO.NORMAL)
        self.assertEqual(workflow.title.value, "Customer journey")
        self.assertEqual(workflow.description.value, "Default customer workflow")
        self.assertEqual(workflow.icon.value, "workflow")
        self.assertEqual(workflow.icon_background.value, "#ffffff")
        self.assertIsNone(workflow.active_workflow_definition_id)

        self.assertEqual(definition.created_at, now)
        self.assertEqual(definition.updated_at, now)
        self.assertEqual(definition.created_by, EntityIdVO.from_value(created_by))
        self.assertEqual(definition.updated_by, EntityIdVO.from_value(created_by))
        self.assertEqual(definition.workflow_application_id, workflow.id)
        self.assertEqual(definition.version.value, "draft")
        self.assertEqual(definition.graph.value, {})
        self.assertEqual(definition.features.value, {})
        self.assertEqual(definition.environment.value, {})
        self.assertEqual(definition.title.value, "")
        self.assertIsNone(definition.description)

        self.assertEqual(result.id, workflow_id)
        self.assertEqual(result.created_at, now)
        self.assertEqual(result.updated_at, now)
        self.assertEqual(result.created_by, created_by)
        self.assertEqual(result.updated_by, created_by)
        self.assertEqual(result.kind, WorkflowKindVO.STANDARD.value)
        self.assertEqual(result.status, WorkflowApplicationStatusVO.NORMAL.value)
        self.assertEqual(result.title, "Customer journey")
        self.assertEqual(result.description, "Default customer workflow")
        self.assertEqual(result.icon, "workflow")
        self.assertEqual(result.icon_background, "#ffffff")
        self.assertIsNone(result.active_workflow_definition_id)


if __name__ == "__main__":
    unittest.main()
