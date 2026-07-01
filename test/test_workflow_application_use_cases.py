from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.shared import EntityIdVO
from src.modules.shared.application.pagination import CursorCodec, InvalidCursorError
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.application.workflow_application import (
    CreateWorkflowCommand,
    CreateWorkflowUseCase,
    ListWorkflowsQuery,
    ListWorkflowsUseCase,
    UpdateWorkflowCommand,
    UpdateWorkflowUseCase,
    WorkflowApplicationCursor,
    WorkflowApplicationListItemDTO,
)
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
    WorkflowApplicationNotFoundError,
    WorkflowApplicationStatusVO,
    WorkflowDefinitionIdVO,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
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
    def __init__(self, workflow=None) -> None:
        self.workflow = workflow
        self.loaded_tenant_id = None
        self.loaded_workflow_id = None
        self.saved_tenant_id = None
        self.saved_workflow = None

    async def load(self, *, tenant_id, workflow_id):
        self.loaded_tenant_id = tenant_id
        self.loaded_workflow_id = workflow_id
        return self.workflow

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


class _WorkflowApplicationQueryRepositoryStub:
    def __init__(self, items) -> None:
        self.items = list(items)
        self.tenant_id = None
        self.limit = None
        self.cursor = None

    async def list(self, *, tenant_id, limit, cursor):
        self.tenant_id = tenant_id
        self.limit = limit
        self.cursor = cursor
        return self.items


def _workflow_item(
    *,
    workflow_id: UUID,
    created_at: datetime,
    title: str,
) -> WorkflowApplicationListItemDTO:
    return WorkflowApplicationListItemDTO(
        id=workflow_id,
        created_at=created_at,
        kind=WorkflowKindVO.STANDARD.value,
        status=WorkflowApplicationStatusVO.NORMAL.value,
        title=title,
        description=None,
        icon="workflow",
        icon_background="#ffffff",
    )


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
        self.assertIsNone(definition.title)
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

    async def test_update_workflow_updates_application_details(self) -> None:
        tenant_id = uuid4()
        workflow_id = uuid4()
        created_by = uuid4()
        updated_by = uuid4()
        created_at = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
        updated_at = datetime(2026, 6, 27, 13, 0, tzinfo=UTC)
        workflow = WorkflowApplicationEntity.create(
            entity_id=WorkflowApplicationIdVO.from_value(workflow_id),
            kind=WorkflowKindVO.STANDARD,
            title=EntityTitleVO("Customer journey"),
            description=EntityDescriptionVO("Default customer workflow"),
            icon=WorkflowIconVO("workflow"),
            icon_background=WorkflowIconBackgroundVO("#ffffff"),
            created_by=EntityIdVO.from_value(created_by),
            now=created_at,
        )
        repository = _WorkflowApplicationRepositoryStub(workflow)
        use_case = UpdateWorkflowUseCase(
            repository=repository,
            clock=_ClockStub(updated_at),
        )

        result = await use_case(
            UpdateWorkflowCommand(
                tenant_id=tenant_id,
                updated_by=updated_by,
                workflow_id=workflow_id,
                title="  Updated journey  ",
                description="  Updated description  ",
                icon="  sparkles  ",
                icon_background="  #111111  ",
            )
        )

        self.assertEqual(repository.loaded_tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(
            repository.loaded_workflow_id,
            WorkflowApplicationIdVO.from_value(workflow_id),
        )
        self.assertEqual(repository.saved_tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertIs(repository.saved_workflow, workflow)
        self.assertEqual(workflow.title.value, "Updated journey")
        self.assertEqual(workflow.description.value, "Updated description")
        self.assertEqual(workflow.icon.value, "sparkles")
        self.assertEqual(workflow.icon_background.value, "#111111")
        self.assertEqual(workflow.updated_by, EntityIdVO.from_value(updated_by))
        self.assertEqual(workflow.updated_at, updated_at)

        self.assertEqual(result.id, workflow_id)
        self.assertEqual(result.created_at, created_at)
        self.assertEqual(result.updated_at, updated_at)
        self.assertEqual(result.created_by, created_by)
        self.assertEqual(result.updated_by, updated_by)
        self.assertEqual(result.title, "Updated journey")
        self.assertEqual(result.description, "Updated description")
        self.assertEqual(result.icon, "sparkles")
        self.assertEqual(result.icon_background, "#111111")

    async def test_update_workflow_converts_blank_description_to_null(self) -> None:
        tenant_id = uuid4()
        workflow_id = uuid4()
        created_by = uuid4()
        updated_by = uuid4()
        now = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
        workflow = WorkflowApplicationEntity.create(
            entity_id=WorkflowApplicationIdVO.from_value(workflow_id),
            kind=WorkflowKindVO.STANDARD,
            title=EntityTitleVO("Customer journey"),
            description=EntityDescriptionVO("Default customer workflow"),
            icon=WorkflowIconVO("workflow"),
            icon_background=WorkflowIconBackgroundVO("#ffffff"),
            created_by=EntityIdVO.from_value(created_by),
            now=now,
        )
        use_case = UpdateWorkflowUseCase(
            repository=_WorkflowApplicationRepositoryStub(workflow),
            clock=_ClockStub(now),
        )

        result = await use_case(
            UpdateWorkflowCommand(
                tenant_id=tenant_id,
                updated_by=updated_by,
                workflow_id=workflow_id,
                title="Customer journey",
                description="  ",
                icon="workflow",
                icon_background="#ffffff",
            )
        )

        self.assertIsNone(workflow.description)
        self.assertIsNone(result.description)

    async def test_update_workflow_raises_not_found(self) -> None:
        use_case = UpdateWorkflowUseCase(
            repository=_WorkflowApplicationRepositoryStub(),
            clock=_ClockStub(datetime(2026, 6, 27, 12, 0, tzinfo=UTC)),
        )

        with self.assertRaises(WorkflowApplicationNotFoundError):
            await use_case(
                UpdateWorkflowCommand(
                    tenant_id=uuid4(),
                    updated_by=uuid4(),
                    workflow_id=uuid4(),
                    title="Customer journey",
                    description=None,
                    icon="workflow",
                    icon_background="#ffffff",
                )
            )

    async def test_list_workflows_returns_items_and_next_cursor(self) -> None:
        tenant_id = uuid4()
        first_id = uuid4()
        second_id = uuid4()
        third_id = uuid4()
        first_created_at = datetime(2026, 6, 27, 12, 2, tzinfo=UTC)
        second_created_at = datetime(2026, 6, 27, 12, 1, tzinfo=UTC)
        third_created_at = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
        repository = _WorkflowApplicationQueryRepositoryStub(
            [
                _workflow_item(
                    workflow_id=first_id,
                    created_at=first_created_at,
                    title="First",
                ),
                _workflow_item(
                    workflow_id=second_id,
                    created_at=second_created_at,
                    title="Second",
                ),
                _workflow_item(
                    workflow_id=third_id,
                    created_at=third_created_at,
                    title="Third",
                ),
            ]
        )
        use_case = ListWorkflowsUseCase(repository=repository)

        result = await use_case(ListWorkflowsQuery(tenant_id=tenant_id, limit=2))

        self.assertEqual(repository.tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(repository.limit, 3)
        self.assertIsNone(repository.cursor)
        self.assertEqual([item.id for item in result.items], [first_id, second_id])
        self.assertIsNotNone(result.next_cursor)
        assert result.next_cursor is not None
        decoded = WorkflowApplicationCursor.decode(result.next_cursor)
        self.assertEqual(decoded.id, str(second_id))
        self.assertEqual(decoded.created_at, second_created_at)
        self.assertEqual(decoded.VERSION, 1)
        self.assertEqual(decoded.SORT, "created_at_desc_id_desc")

    async def test_list_workflows_returns_no_cursor_without_extra_row(self) -> None:
        tenant_id = uuid4()
        workflow_id = uuid4()
        created_at = datetime(2026, 6, 27, 12, 0, tzinfo=UTC)
        repository = _WorkflowApplicationQueryRepositoryStub(
            [
                _workflow_item(
                    workflow_id=workflow_id,
                    created_at=created_at,
                    title="Only",
                ),
            ]
        )
        use_case = ListWorkflowsUseCase(repository=repository)

        result = await use_case(ListWorkflowsQuery(tenant_id=tenant_id, limit=2))

        self.assertEqual(len(result.items), 1)
        self.assertIsNone(result.next_cursor)

    async def test_list_workflows_passes_decoded_cursor_to_repository(self) -> None:
        tenant_id = uuid4()
        cursor = WorkflowApplicationCursor(
            created_at=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
            id=str(uuid4()),
        )
        repository = _WorkflowApplicationQueryRepositoryStub([])
        use_case = ListWorkflowsUseCase(repository=repository)

        await use_case(
            ListWorkflowsQuery(
                tenant_id=tenant_id,
                limit=50,
                cursor=cursor.encode(),
            )
        )

        self.assertEqual(repository.cursor, cursor)

    async def test_list_workflows_rejects_invalid_cursor(self) -> None:
        use_case = ListWorkflowsUseCase(
            repository=_WorkflowApplicationQueryRepositoryStub([])
        )

        with self.assertRaises(InvalidCursorError):
            await use_case(
                ListWorkflowsQuery(
                    tenant_id=uuid4(),
                    limit=50,
                    cursor="not-a-valid-cursor",
                )
            )

    async def test_list_workflows_rejects_cursor_with_wrong_version(self) -> None:
        use_case = ListWorkflowsUseCase(
            repository=_WorkflowApplicationQueryRepositoryStub([])
        )
        cursor = CursorCodec.encode(
            {
                "v": 2,
                "sort": WorkflowApplicationCursor.SORT,
                "created_at": datetime(2026, 6, 27, 12, 0, tzinfo=UTC).isoformat(),
                "id": str(uuid4()),
            }
        )

        with self.assertRaises(InvalidCursorError):
            await use_case(
                ListWorkflowsQuery(
                    tenant_id=uuid4(),
                    limit=50,
                    cursor=cursor,
                )
            )

    async def test_list_workflows_rejects_cursor_with_wrong_sort(self) -> None:
        use_case = ListWorkflowsUseCase(
            repository=_WorkflowApplicationQueryRepositoryStub([])
        )
        cursor = CursorCodec.encode(
            {
                "v": WorkflowApplicationCursor.VERSION,
                "sort": "created_at_asc_id_asc",
                "created_at": datetime(2026, 6, 27, 12, 0, tzinfo=UTC).isoformat(),
                "id": str(uuid4()),
            }
        )

        with self.assertRaises(InvalidCursorError):
            await use_case(
                ListWorkflowsQuery(
                    tenant_id=uuid4(),
                    limit=50,
                    cursor=cursor,
                )
            )


if __name__ == "__main__":
    unittest.main()
