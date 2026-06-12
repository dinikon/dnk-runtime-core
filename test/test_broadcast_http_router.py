from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.broadcast.application.broadcast.dto import (
    BroadcastDTO,
    BroadcastFieldDescriptionDTO,
    BroadcastFieldOptionDTO,
    BroadcastFieldsDescriptionDTO,
    BroadcastListDTO,
    BroadcastObjectDescriptionDTO,
)
from src.modules.broadcast.presentation.http.broadcast.controller.create_broadcast import (
    create_broadcast,
)
from src.modules.broadcast.presentation.http.broadcast.controller.describe_broadcast_fields import (
    describe_broadcast_fields,
)
from src.modules.broadcast.presentation.http.broadcast.controller.get_broadcast import (
    get_broadcast,
)
from src.modules.broadcast.presentation.http.broadcast.controller.list_broadcasts import (
    list_broadcasts,
)
from src.modules.runtime_data.application.query.capabilities.field_query_capability import (
    FieldFilterCapability,
    FieldSortCapability,
)
from src.modules.broadcast.presentation.http.broadcast.requests import (
    BroadcastListPaginationRequestSchema,
    CreateBroadcastRequestSchema,
    GetBroadcastRequestSchema,
    ListBroadcastsRequestSchema,
)
from src.modules.runtime_data.domain.error import (
    RuntimeDataFilterError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import RuntimeObjectNotFoundError
from src.modules.shared import DomainError, EntityIdVO, Principal, RequestContext


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


class BroadcastHttpRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_broadcast_returns_response_shape(self) -> None:
        now = datetime.now(UTC)
        broadcast_id = uuid4()
        use_case = _UseCaseStub(
            BroadcastDTO(
                id=broadcast_id,
                created_at=now,
                updated_at=now,
                title="June broadcast",
                description=None,
                status="DRAFT",
            )
        )

        response = await create_broadcast(
            payload=CreateBroadcastRequestSchema(
                title="June broadcast",
                description=None,
            ),
            context=_context(),
            use_case=use_case,
        )

        self.assertEqual(response.id, broadcast_id)
        self.assertEqual(response.created_at, now)
        self.assertEqual(response.updated_at, now)
        self.assertEqual(response.title, "June broadcast")
        self.assertIsNone(response.description)
        self.assertEqual(response.status, "DRAFT")
        self.assertEqual(use_case.command.title, "June broadcast")
        self.assertIsNone(use_case.command.description)

    async def test_create_broadcast_returns_401_without_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_broadcast(
                payload=CreateBroadcastRequestSchema(title="June broadcast"),
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_create_broadcast_schema_runtime_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_broadcast(
                payload=CreateBroadcastRequestSchema(title="June broadcast"),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="broadcast",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_create_broadcast_validation_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_broadcast(
                payload=CreateBroadcastRequestSchema(title=""),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataValidationError("Field 'title' must not be empty.")
                ),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_list_broadcasts_returns_page_response_shape(self) -> None:
        now = datetime.now(UTC)
        broadcast_id = uuid4()
        context = _context()
        use_case = _UseCaseStub(
            BroadcastListDTO(
                items=(
                    BroadcastDTO(
                        id=broadcast_id,
                        created_at=now,
                        updated_at=now,
                        title="June broadcast",
                        description=None,
                        status="DRAFT",
                    ),
                ),
                total=123,
                limit=25,
                offset=50,
            )
        )
        filter_dsl = {"field": "status", "op": "eq", "value": "DRAFT"}
        sort_dsl = [{"field": "created_at", "direction": "desc"}]

        response = await list_broadcasts(
            payload=ListBroadcastsRequestSchema(
                filter=filter_dsl,
                sort=sort_dsl,
                pagination=BroadcastListPaginationRequestSchema(
                    limit=25,
                    offset=50,
                ),
            ),
            context=context,
            use_case=use_case,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0].id, broadcast_id)
        self.assertEqual(response.data[0].created_at, now)
        self.assertEqual(response.data[0].updated_at, now)
        self.assertEqual(response.data[0].title, "June broadcast")
        self.assertIsNone(response.data[0].description)
        self.assertEqual(response.data[0].status, "DRAFT")
        self.assertEqual(response.pagination.limit, 25)
        self.assertEqual(response.pagination.offset, 50)
        self.assertEqual(response.pagination.total, 123)
        self.assertEqual(use_case.command.tenant_id, context.principal.tenant_id)
        self.assertEqual(use_case.command.filter_dsl, filter_dsl)
        self.assertEqual(use_case.command.sort_dsl, sort_dsl)
        self.assertEqual(use_case.command.limit, 25)
        self.assertEqual(use_case.command.offset, 50)

    async def test_list_broadcasts_returns_401_without_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_broadcasts(
                payload=ListBroadcastsRequestSchema(),
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_list_broadcasts_schema_runtime_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_broadcasts(
                payload=ListBroadcastsRequestSchema(),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="broadcast",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_list_broadcasts_filter_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_broadcasts(
                payload=ListBroadcastsRequestSchema(),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataFilterError(
                        code="INVALID_FILTER_DSL",
                        message="Invalid filter.",
                    )
                ),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_get_broadcast_returns_response_shape(self) -> None:
        now = datetime.now(UTC)
        broadcast_id = uuid4()
        context = _context()
        use_case = _UseCaseStub(
            BroadcastDTO(
                id=broadcast_id,
                created_at=now,
                updated_at=now,
                title="June broadcast",
                description=None,
                status="DRAFT",
            )
        )

        response = await get_broadcast(
            payload=GetBroadcastRequestSchema(id=broadcast_id),
            context=context,
            use_case=use_case,
        )

        self.assertEqual(response.id, broadcast_id)
        self.assertEqual(response.created_at, now)
        self.assertEqual(response.updated_at, now)
        self.assertEqual(response.title, "June broadcast")
        self.assertIsNone(response.description)
        self.assertEqual(response.status, "DRAFT")
        self.assertEqual(use_case.command.tenant_id, context.principal.tenant_id)
        self.assertEqual(use_case.command.broadcast_id, broadcast_id)

    async def test_get_broadcast_returns_401_without_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await get_broadcast(
                payload=GetBroadcastRequestSchema(id=uuid4()),
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_get_broadcast_returns_404_when_row_is_missing(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await get_broadcast(
                payload=GetBroadcastRequestSchema(id=uuid4()),
                context=_context(),
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)

    async def test_get_broadcast_schema_runtime_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await get_broadcast(
                payload=GetBroadcastRequestSchema(id=uuid4()),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="broadcast",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_get_broadcast_validation_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await get_broadcast(
                payload=GetBroadcastRequestSchema(id=uuid4()),
                context=_context(),
                use_case=_FailingUseCase(RuntimeDataValidationError("Invalid id.")),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_describe_broadcast_fields_returns_response_shape(self) -> None:
        object_id = uuid4()
        field_id = uuid4()
        context = _context()
        use_case = _UseCaseStub(
            BroadcastFieldsDescriptionDTO(
                object_description=BroadcastObjectDescriptionDTO(
                    id=object_id,
                    singular_label="Broadcast",
                    plural_label="Broadcasts",
                    description="Tenant broadcast definitions.",
                    kind="standard",
                ),
                fields=(
                    BroadcastFieldDescriptionDTO(
                        id=field_id,
                        field_name="status",
                        label="Status",
                        description="Broadcast lifecycle status.",
                        type="text",
                        kind="standard",
                        is_nullable=False,
                        default_value="'DRAFT'",
                        options=(
                            BroadcastFieldOptionDTO(
                                value="DRAFT",
                                label="Draft",
                            ),
                        ),
                        filter=FieldFilterCapability(
                            enabled=True,
                            operators=("eq", "in"),
                            input="text",
                            value_type="string",
                            options=(
                                {
                                    "value": "DRAFT",
                                    "label": "Draft",
                                },
                            ),
                        ),
                        sort=FieldSortCapability(enabled=True),
                    ),
                ),
            )
        )

        response = await describe_broadcast_fields(
            context=context,
            use_case=use_case,
        )

        self.assertEqual(response.object.id, object_id)
        self.assertEqual(response.object.singular_label, "Broadcast")
        self.assertEqual(response.object.plural_label, "Broadcasts")
        self.assertEqual(response.object.kind, "standard")
        self.assertEqual(len(response.fields), 1)
        self.assertEqual(response.fields[0].id, field_id)
        self.assertEqual(response.fields[0].field_name, "status")
        self.assertEqual(response.fields[0].type, "text")
        self.assertFalse(response.fields[0].is_nullable)
        self.assertEqual(response.fields[0].default_value, "'DRAFT'")
        self.assertEqual(response.fields[0].options[0].value, "DRAFT")
        self.assertTrue(response.fields[0].filter.enabled)
        self.assertEqual(response.fields[0].filter.operators, ["eq", "in"])
        self.assertEqual(response.fields[0].filter.input, "text")
        self.assertEqual(response.fields[0].filter.value_type, "string")
        self.assertEqual(response.fields[0].filter.options[0].value, "DRAFT")
        self.assertTrue(response.fields[0].sort.enabled)
        self.assertEqual(
            use_case.command,
            EntityIdVO.from_value(context.principal.tenant_id),
        )

    async def test_describe_broadcast_fields_returns_401_without_principal(
        self,
    ) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_broadcast_fields(
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_UseCaseStub(None),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_describe_broadcast_fields_schema_runtime_error_returns_409(
        self,
    ) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_broadcast_fields(
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="broadcast",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_describe_broadcast_fields_domain_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_broadcast_fields(
                context=_context(),
                use_case=_FailingUseCase(DomainError("Invalid broadcast fields.")),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
