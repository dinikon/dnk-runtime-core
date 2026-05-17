from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
    ObjectFeatureConfigListDTO,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.list_object_features_controller import (
    list_object_features,
)
from src.modules.schema_registry.presentation.http.object_feature.request import (
    ListObjectFeaturesRequestSchema,
)
from src.modules.shared import Principal, RequestContext


def _context(*, with_tenant: bool = True) -> RequestContext:
    return RequestContext(
        principal=(
            Principal(
                user_id=str(uuid4()),
                tenant_id=str(uuid4()),
                session_id=str(uuid4()),
                roles=(),
            )
            if with_tenant
            else None
        ),
        request_id=None,
        ip=None,
        user_agent=None,
    )


class _UseCaseSpy:
    def __init__(self, result: ObjectFeatureConfigListDTO) -> None:
        self.query = None
        self._result = result

    async def __call__(self, query):
        self.query = query
        return self._result


class SchemaRegistryObjectFeatureHttpListControllerTests(
    unittest.IsolatedAsyncioTestCase,
):
    async def test_success_returns_response_and_passes_query(self) -> None:
        now = datetime.now(UTC)
        object_id = uuid4()
        use_case = _UseCaseSpy(
            ObjectFeatureConfigListDTO(
                items=[
                    ObjectFeatureConfigDTO(
                        id=uuid4(),
                        created_at=now,
                        updated_at=now,
                        object_id=object_id,
                        feature_code="CONTACT_POINT",
                        kind="custom",
                        status="enabled",
                        config={"fields": ["email"]},
                        is_locked=False,
                        locked_reason=None,
                    )
                ],
                count=1,
            )
        )

        response = await list_object_features(
            payload=ListObjectFeaturesRequestSchema(object_id=object_id),
            context=_context(),
            use_case=use_case,
        )

        self.assertEqual(response.count, 1)
        self.assertEqual(response.items[0].feature_code, "CONTACT_POINT")
        self.assertEqual(use_case.query.object_id.uuid, object_id)

    async def test_no_tenant_returns_401(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_object_features(
                payload=ListObjectFeaturesRequestSchema(object_id=uuid4()),
                context=_context(with_tenant=False),
                use_case=_UseCaseSpy(ObjectFeatureConfigListDTO(items=[], count=0)),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)


__all__ = ["SchemaRegistryObjectFeatureHttpListControllerTests"]
