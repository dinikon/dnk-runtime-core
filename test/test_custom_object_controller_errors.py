from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.custom_object.application.record.dto import CustomRecordDTO
from src.modules.custom_object.domain import CustomObjectNotFoundError
from src.modules.custom_object.presentation.http.object.controller.describe_custom_object import (
    describe_custom_object,
)
from src.modules.custom_object.presentation.http.object.requests import (
    ObjectIdRequestSchema,
)
from src.modules.custom_object.presentation.http.record.controller.list_custom_records import (
    list_custom_records,
)
from src.modules.custom_object.presentation.http.record.requests import (
    ListCustomRecordsRequestSchema,
)
from src.modules.shared import EntityIdVO, Principal, RequestContext


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


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, command):
        raise self._exc


class CustomObjectControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_describe_missing_object_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_custom_object(
                payload=ObjectIdRequestSchema(object_id=uuid4()),
                context=_context(),
                use_case=_FailingUseCase(CustomObjectNotFoundError("missing")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)

    async def test_list_records_parses_filter_sort_and_tenant(self) -> None:
        context = _context()
        object_id = uuid4()
        row_id = uuid4()
        now = datetime.now(UTC)
        recorded_query = None

        class UseCaseStub:
            async def __call__(self, query):
                nonlocal recorded_query
                recorded_query = query
                return [
                    CustomRecordDTO(
                        object_id=object_id,
                        row_id=row_id,
                        values={
                            "id": row_id,
                            "created_at": now,
                            "updated_at": now,
                            "name": "Acme",
                        },
                    )
                ]

        response = await list_custom_records(
            payload=ListCustomRecordsRequestSchema(
                object_id=object_id,
                filter={
                    "or": [
                        {"field": "name", "op": "contains", "value": "Ac"},
                        {"field": "status", "op": "eq", "value": "new"},
                    ]
                },
                sort={"created_at": "DESC"},
                limit=10,
                offset=5,
            ),
            context=context,
            use_case=UseCaseStub(),
        )

        self.assertEqual(
            recorded_query.tenant_id,
            EntityIdVO.from_value(context.principal.tenant_id),
        )
        self.assertEqual(recorded_query.object_id.uuid, object_id)
        self.assertEqual(recorded_query.filters[0].logic, "or")
        self.assertEqual(recorded_query.sorting[0].direction, "desc")
        self.assertEqual(response.limit, 10)
        self.assertEqual(response.offset, 5)
        self.assertEqual(response.count, 1)


__all__ = ["CustomObjectControllerTests"]
