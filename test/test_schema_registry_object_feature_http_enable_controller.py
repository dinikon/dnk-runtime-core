from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.enable_object_feature_controller import (
    enable_object_feature,
)
from src.modules.schema_registry.presentation.http.object_feature.request import (
    EnableObjectFeatureRequestSchema,
)
from src.modules.shared import Principal, RequestContext


def _context(*, tenant_id: str | None = None) -> RequestContext:
    return RequestContext(
        principal=(
            Principal(
                user_id=str(uuid4()),
                tenant_id=tenant_id or str(uuid4()),
                session_id=str(uuid4()),
                roles=(),
            )
            if tenant_id is not None
            else None
        ),
        request_id=None,
        ip=None,
        user_agent=None,
    )


def _dto(*, object_id) -> ObjectFeatureConfigDTO:
    now = datetime.now(UTC)
    return ObjectFeatureConfigDTO(
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


class _UseCaseSpy:
    def __init__(self) -> None:
        self.command = None

    async def __call__(self, command):
        self.command = command
        return _dto(object_id=command.object_id.uuid)


class SchemaRegistryObjectFeatureHttpEnableControllerTests(
    unittest.IsolatedAsyncioTestCase,
):
    async def test_success_returns_response_and_passes_command(self) -> None:
        object_id = uuid4()
        tenant_id = str(uuid4())
        use_case = _UseCaseSpy()

        response = await enable_object_feature(
            payload=EnableObjectFeatureRequestSchema(
                object_id=object_id,
                feature_code="CONTACT_POINT",
                config={"fields": ["email"]},
            ),
            context=_context(tenant_id=tenant_id),
            use_case=use_case,
        )

        self.assertEqual(response.object_id, object_id)
        self.assertEqual(response.feature_code, "CONTACT_POINT")
        self.assertEqual(str(use_case.command.tenant_id), tenant_id)
        self.assertEqual(use_case.command.config, {"fields": ["email"]})

    async def test_no_tenant_returns_401(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await enable_object_feature(
                payload=EnableObjectFeatureRequestSchema(
                    object_id=uuid4(),
                    feature_code="CONTACT_POINT",
                ),
                context=_context(),
                use_case=_UseCaseSpy(),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_invalid_feature_code_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await enable_object_feature(
                payload=EnableObjectFeatureRequestSchema(
                    object_id=uuid4(),
                    feature_code="UNKNOWN",
                ),
                context=_context(tenant_id=str(uuid4())),
                use_case=_UseCaseSpy(),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


__all__ = ["SchemaRegistryObjectFeatureHttpEnableControllerTests"]
