from __future__ import annotations

import unittest
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.schema_registry.domain.error import ObjectNotFoundError
from src.modules.schema_registry.presentation.http.config.object.controller.describe_custom_object import (
    describe_custom_object,
)
from src.modules.schema_registry.presentation.http.config.object.requests import (
    ObjectIdRequestSchema,
)
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


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, command):
        raise self._exc


class SchemaConfigObjectControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_describe_missing_object_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_custom_object(
                payload=ObjectIdRequestSchema(object_id=uuid4()),
                context=_context(),
                use_case=_FailingUseCase(ObjectNotFoundError("missing")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
