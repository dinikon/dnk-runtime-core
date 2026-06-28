from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.runtime_data.domain.error import RuntimeDataValidationError
from src.modules.schema_registry.domain.error import RuntimeObjectNotFoundError
from src.modules.shared import Principal, RequestContext
from src.modules.workflow.application.workflow_application.dto import (
    WorkflowApplicationDTO,
    WorkflowApplicationListDTO,
    WorkflowApplicationListItemDTO,
)
from src.modules.workflow.presentation.http.workflow_application.controller.list_workflows import (
    list_workflows,
)
from src.modules.workflow.presentation.http.router import router
from src.modules.workflow.presentation.http.workflow_application.controller.create_workflow import (
    create_workflow,
)
from src.modules.workflow.presentation.http.workflow_application.requests import (
    CreateWorkflowRequestSchema,
)


def _context() -> RequestContext:
    return RequestContext(
        principal=Principal(
            user_id=str(uuid4()),
            tenant_id=str(uuid4()),
            session_id=str(uuid4()),
            roles=(),
        ),
        request_id=None,
        ip=None,
        user_agent=None,
    )


class _UseCaseStub:
    def __init__(self, result) -> None:
        self.result = result
        self.command = None

    async def __call__(self, command):
        self.command = command
        return self.result


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, command):
        raise self._exc


class WorkflowHttpRouterTests(unittest.IsolatedAsyncioTestCase):
    def test_router_exposes_create_workflow_route(self) -> None:
        route_candidates = []
        for route in router.routes:
            nested_router = getattr(route, "original_router", None)
            if nested_router is None:
                route_candidates.append(route)
            else:
                route_candidates.extend(nested_router.routes)
        routes = {
            (method, route.path)
            for route in route_candidates
            for method in getattr(route, "methods", set()) or set()
        }

        self.assertIn(("POST", "/workflows"), routes)
        self.assertIn(("GET", "/workflows"), routes)

    async def test_create_workflow_returns_response_shape(self) -> None:
        now = datetime.now(UTC)
        workflow_id = uuid4()
        created_by = uuid4()
        context = _context()
        use_case = _UseCaseStub(
            WorkflowApplicationDTO(
                id=workflow_id,
                created_at=now,
                updated_at=now,
                created_by=created_by,
                updated_by=created_by,
                kind="STANDARD",
                status="NORMAL",
                title="Customer journey",
                description=None,
                icon="workflow",
                icon_background="#ffffff",
                active_workflow_definition_id=None,
            )
        )

        response = await create_workflow(
            payload=CreateWorkflowRequestSchema(
                title="Customer journey",
                description=None,
                icon="workflow",
                icon_background="#ffffff",
            ),
            context=context,
            use_case=use_case,
        )

        self.assertEqual(response.id, workflow_id)
        self.assertEqual(response.created_at, now)
        self.assertEqual(response.updated_at, now)
        self.assertEqual(response.created_by, created_by)
        self.assertEqual(response.updated_by, created_by)
        self.assertEqual(response.kind, "STANDARD")
        self.assertEqual(response.status, "NORMAL")
        self.assertEqual(response.title, "Customer journey")
        self.assertIsNone(response.description)
        self.assertEqual(response.icon, "workflow")
        self.assertEqual(response.icon_background, "#ffffff")
        self.assertIsNone(response.active_workflow_definition_id)
        self.assertEqual(use_case.command.tenant_id, context.principal.tenant_id)
        self.assertEqual(use_case.command.created_by, context.principal.user_id)
        self.assertEqual(use_case.command.title, "Customer journey")
        self.assertEqual(use_case.command.icon, "workflow")

    async def test_list_workflows_returns_response_shape(self) -> None:
        now = datetime.now(UTC)
        workflow_id = uuid4()
        context = _context()
        use_case = _UseCaseStub(
            WorkflowApplicationListDTO(
                items=(
                    WorkflowApplicationListItemDTO(
                        id=workflow_id,
                        created_at=now,
                        kind="STANDARD",
                        status="NORMAL",
                        title="Customer journey",
                        description=None,
                        icon="workflow",
                        icon_background="#ffffff",
                    ),
                ),
                next_cursor="next",
            )
        )

        response = await list_workflows(
            context=context,
            use_case=use_case,
            limit=50,
            cursor=None,
        )

        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.items[0].id, workflow_id)
        self.assertEqual(response.items[0].created_at, now)
        self.assertEqual(response.items[0].kind, "STANDARD")
        self.assertEqual(response.items[0].status, "NORMAL")
        self.assertEqual(response.items[0].title, "Customer journey")
        self.assertIsNone(response.items[0].description)
        self.assertEqual(response.items[0].icon, "workflow")
        self.assertEqual(response.items[0].icon_background, "#ffffff")
        self.assertEqual(response.next_cursor, "next")
        self.assertEqual(use_case.command.tenant_id, context.principal.tenant_id)
        self.assertEqual(use_case.command.limit, 50)
        self.assertIsNone(use_case.command.cursor)

    async def test_create_workflow_returns_401_without_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_workflow(
                payload=CreateWorkflowRequestSchema(
                    title="Customer journey",
                    icon="workflow",
                    icon_background="#ffffff",
                ),
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_list_workflows_returns_401_without_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_workflows(
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_UseCaseStub(None),
                limit=50,
                cursor=None,
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_create_workflow_returns_401_without_tenant(self) -> None:
        context = RequestContext(
            principal=Principal(
                user_id=str(uuid4()),
                tenant_id=None,
                session_id=str(uuid4()),
                roles=(),
            ),
            request_id=None,
            ip=None,
            user_agent=None,
        )

        with self.assertRaises(HTTPException) as caught:
            await create_workflow(
                payload=CreateWorkflowRequestSchema(
                    title="Customer journey",
                    icon="workflow",
                    icon_background="#ffffff",
                ),
                context=context,
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_create_workflow_returns_401_without_user(self) -> None:
        context = RequestContext(
            principal=Principal(
                user_id="",
                tenant_id=str(uuid4()),
                session_id=str(uuid4()),
                roles=(),
            ),
            request_id=None,
            ip=None,
            user_agent=None,
        )

        with self.assertRaises(HTTPException) as caught:
            await create_workflow(
                payload=CreateWorkflowRequestSchema(
                    title="Customer journey",
                    icon="workflow",
                    icon_background="#ffffff",
                ),
                context=context,
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_create_workflow_schema_runtime_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_workflow(
                payload=CreateWorkflowRequestSchema(
                    title="Customer journey",
                    icon="workflow",
                    icon_background="#ffffff",
                ),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="workflow_application",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_create_workflow_validation_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_workflow(
                payload=CreateWorkflowRequestSchema(
                    title="",
                    icon="workflow",
                    icon_background="#ffffff",
                ),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataValidationError("Field 'title' must not be empty.")
                ),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_list_workflows_invalid_cursor_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_workflows(
                context=_context(),
                use_case=_FailingUseCase(ValueError("Invalid workflow cursor.")),
                limit=50,
                cursor="invalid",
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


if __name__ == "__main__":
    unittest.main()
