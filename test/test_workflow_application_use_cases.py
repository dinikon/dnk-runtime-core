from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.shared import EntityIdVO
from src.modules.shared.application.pagination import CursorCodec, InvalidCursorError
from src.modules.workflow.application.workflow_application import (
    CreateWorkflowCommand,
    CreateWorkflowUseCase,
    ListWorkflowsQuery,
    ListWorkflowsUseCase,
    WorkflowApplicationCursor,
    WorkflowApplicationListItemDTO,
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
