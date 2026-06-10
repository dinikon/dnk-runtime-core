from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.broadcast.application.broadcast.dto import BroadcastDTO
from src.modules.broadcast.presentation.http.broadcast.controller.create_broadcast import (
    create_broadcast,
)
from src.modules.broadcast.presentation.http.broadcast.requests import (
    CreateBroadcastRequestSchema,
)
from src.modules.runtime_data.domain.error import RuntimeDataValidationError
from src.modules.schema_registry.domain.error import RuntimeObjectNotFoundError
from src.modules.shared import Principal, RequestContext


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
