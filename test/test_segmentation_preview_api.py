from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)
from src.modules.segmentation.application.segment_version import (
    SegmentPreviewDTO,
    SegmentVersionActiveVersionNotFoundError,
    SegmentVersionDslError,
)
from src.modules.segmentation.presentation.http.router import router
from src.modules.segmentation.presentation.http.segment_definition.controllers.preview_segment_definition import (
    preview_segment_definition,
)
from src.modules.segmentation.presentation.http.segment_definition.requests import (
    PreviewSegmentDefinitionRequestSchema,
)
from src.modules.segmentation.presentation.http.segment_version.controllers.preview_segment_config import (
    preview_segment_config,
)
from src.modules.segmentation.presentation.http.segment_version.controllers.preview_segment_version import (
    preview_segment_version,
)
from src.modules.segmentation.presentation.http.segment_version.requests import (
    PreviewSegmentConfigRequestSchema,
    PreviewSegmentVersionRequestSchema,
)
from src.modules.shared import EntityIdVO


class _UseCaseStub:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self.result = result
        self.exc = exc
        self.command = None

    async def __call__(self, command):
        self.command = command
        if self.exc is not None:
            raise self.exc
        return self.result


def _context(tenant_id):
    return SimpleNamespace(principal=SimpleNamespace(tenant_id=tenant_id))


def _preview_dto(contact_id):
    return SegmentPreviewDTO(
        contact_ids=(contact_id,),
        contacts=(
            ContactSummaryDTO(
                id=contact_id,
                first_name="Denis",
                last_name=None,
                middle_name=None,
                status="active",
            ),
        ),
        limit=50,
        offset=0,
        count=1,
        total=None,
        has_more=False,
    )


class SegmentationPreviewApiTests(unittest.IsolatedAsyncioTestCase):
    def test_router_exposes_preview_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/segments/preview"), routes)
        self.assertIn(("POST", "/segments/{segment_id}/preview"), routes)
        self.assertIn(
            (
                "POST",
                "/segments/{segment_id}/versions/{segment_version_id}/preview",
            ),
            routes,
        )

    def test_preview_request_schemas_validate_limit_and_offset(self) -> None:
        with self.assertRaises(ValidationError):
            PreviewSegmentConfigRequestSchema(config={}, limit=0)
        with self.assertRaises(ValidationError):
            PreviewSegmentDefinitionRequestSchema(offset=-1)
        with self.assertRaises(ValidationError):
            PreviewSegmentVersionRequestSchema(limit=101)

    async def test_preview_config_maps_command_and_response(self) -> None:
        tenant_id = uuid4()
        contact_id = uuid4()
        use_case = _UseCaseStub(_preview_dto(contact_id))

        response = await preview_segment_config(
            payload=PreviewSegmentConfigRequestSchema(
                config={"root_object": "contact"},
                limit=50,
                offset=0,
                include_contact_summary=True,
            ),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(use_case.command.tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(use_case.command.config, {"root_object": "contact"})
        self.assertEqual(response.contact_ids, [contact_id])
        self.assertEqual(response.items[0].first_name, "Denis")
        self.assertIsNone(response.total)

    async def test_preview_definition_maps_query_and_response(self) -> None:
        tenant_id = uuid4()
        segment_id = uuid4()
        version_id = uuid4()
        contact_id = uuid4()
        use_case = _UseCaseStub(_preview_dto(contact_id))

        response = await preview_segment_definition(
            segment_id=segment_id,
            payload=PreviewSegmentDefinitionRequestSchema(
                segment_version_id=version_id,
                include_contact_summary=False,
            ),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(use_case.command.segment_id.uuid, segment_id)
        self.assertEqual(use_case.command.segment_version_id.uuid, version_id)
        self.assertFalse(use_case.command.include_contact_summary)
        self.assertEqual(response.contact_ids, [contact_id])

    async def test_preview_version_maps_query_and_response(self) -> None:
        tenant_id = uuid4()
        segment_id = uuid4()
        version_id = uuid4()
        contact_id = uuid4()
        use_case = _UseCaseStub(_preview_dto(contact_id))

        response = await preview_segment_version(
            segment_id=segment_id,
            segment_version_id=version_id,
            payload=PreviewSegmentVersionRequestSchema(),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(use_case.command.segment_id.uuid, segment_id)
        self.assertEqual(use_case.command.segment_version_id.uuid, version_id)
        self.assertEqual(response.count, 1)

    async def test_preview_requires_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await preview_segment_config(
                payload=PreviewSegmentConfigRequestSchema(config={}),
                context=SimpleNamespace(principal=None),
                use_case=_UseCaseStub(),
            )

        self.assertEqual(caught.exception.status_code, 401)

    async def test_preview_maps_dsl_error_to_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await preview_segment_config(
                payload=PreviewSegmentConfigRequestSchema(config={}),
                context=_context(uuid4()),
                use_case=_UseCaseStub(
                    exc=SegmentVersionDslError(
                        "root_object must be contact.",
                        path="root_object",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, 422)

    async def test_preview_maps_missing_active_version_to_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await preview_segment_definition(
                segment_id=uuid4(),
                payload=PreviewSegmentDefinitionRequestSchema(),
                context=_context(uuid4()),
                use_case=_UseCaseStub(
                    exc=SegmentVersionActiveVersionNotFoundError(str(uuid4()))
                ),
            )

        self.assertEqual(caught.exception.status_code, 409)


__all__ = ["SegmentationPreviewApiTests"]
