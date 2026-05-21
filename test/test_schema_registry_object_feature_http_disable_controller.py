from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigLockedError,
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.disable_object_feature_controller import (
    disable_object_feature,
)
from src.modules.schema_registry.presentation.http.object_feature.request import (
    ObjectFeatureRequestSchema,
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


class _UseCaseStub:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self.command = None
        self._result = result
        self._exc = exc

    async def __call__(self, command):
        self.command = command
        if self._exc is not None:
            raise self._exc
        return self._result


class SchemaRegistryObjectFeatureHttpDisableControllerTests(
    unittest.IsolatedAsyncioTestCase,
):
    async def test_success_returns_response(self) -> None:
        now = datetime.now(UTC)
        object_id = uuid4()
        use_case = _UseCaseStub(
            result=ObjectFeatureConfigDTO(
                id=uuid4(),
                created_at=now,
                updated_at=now,
                object_id=object_id,
                feature_code="CONTACT_POINT",
                kind="custom",
                status="disabled",
                config={},
                is_locked=False,
                locked_reason=None,
            )
        )

        response = await disable_object_feature(
            payload=ObjectFeatureRequestSchema(
                object_id=object_id,
                feature_code="CONTACT_POINT",
            ),
            context=_context(),
            use_case=use_case,
        )

        self.assertEqual(response.status, "disabled")
        self.assertEqual(use_case.command.feature_code.value, "CONTACT_POINT")

    async def test_not_found_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await disable_object_feature(
                payload=ObjectFeatureRequestSchema(
                    object_id=uuid4(),
                    feature_code="CONTACT_POINT",
                ),
                context=_context(),
                use_case=_UseCaseStub(exc=ObjectFeatureConfigNotFoundError("missing")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)

    async def test_locked_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await disable_object_feature(
                payload=ObjectFeatureRequestSchema(
                    object_id=uuid4(),
                    feature_code="CONTACT_POINT",
                ),
                context=_context(),
                use_case=_UseCaseStub(exc=ObjectFeatureConfigLockedError("locked")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)


__all__ = ["SchemaRegistryObjectFeatureHttpDisableControllerTests"]
