from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.get_object_feature_config_controller import (
    get_object_feature_config,
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
        self.query = None
        self._result = result
        self._exc = exc

    async def __call__(self, query):
        self.query = query
        if self._exc is not None:
            raise self._exc
        return self._result


class SchemaRegistryObjectFeatureHttpGetControllerTests(
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
                status="enabled",
                config={},
                is_locked=False,
                locked_reason=None,
            )
        )

        response = await get_object_feature_config(
            payload=ObjectFeatureRequestSchema(
                object_id=object_id,
                feature_code="CONTACT_POINT",
            ),
            context=_context(),
            use_case=use_case,
        )

        self.assertEqual(response.object_id, object_id)
        self.assertEqual(use_case.query.feature_code.value, "CONTACT_POINT")

    async def test_not_found_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await get_object_feature_config(
                payload=ObjectFeatureRequestSchema(
                    object_id=uuid4(),
                    feature_code="CONTACT_POINT",
                ),
                context=_context(),
                use_case=_UseCaseStub(exc=ObjectFeatureConfigNotFoundError("missing")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)


__all__ = ["SchemaRegistryObjectFeatureHttpGetControllerTests"]
