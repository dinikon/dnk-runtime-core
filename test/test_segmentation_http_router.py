from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from src.modules.segmentation.application.segment_static_member import (
    ContactSummaryDTO,
    StaticMemberDTO,
)
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMemberContactNotFoundError,
)
from src.modules.segmentation.presentation.http.router import router
from src.modules.segmentation.presentation.http.segment_static_member.controllers.add_static_member import (
    add_static_member,
)
from src.modules.segmentation.presentation.http.segment_static_member.controllers.list_static_members import (
    list_static_members,
)
from src.modules.segmentation.presentation.http.segment_static_member.controllers.remove_static_member import (
    remove_static_member,
)
from src.modules.segmentation.presentation.http.segment_static_member.requests import (
    AddStaticMemberRequestSchema,
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


class SegmentationHttpRouterTests(unittest.IsolatedAsyncioTestCase):
    def test_router_exposes_static_member_routes(self) -> None:
        routes = {
            (method, route.path)
            for route in router.routes
            for method in route.methods or set()
        }

        self.assertIn(("POST", "/segments/{segment_id}/static-members"), routes)
        self.assertIn(("GET", "/segments/{segment_id}/static-members"), routes)
        self.assertIn(
            ("DELETE", "/segments/{segment_id}/static-members/{contact_id}"),
            routes,
        )

    async def test_add_static_member_maps_command_and_response_explicitly(
        self,
    ) -> None:
        tenant_id = uuid4()
        segment_id = uuid4()
        contact_id = uuid4()
        member_id = uuid4()
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        use_case = _UseCaseStub(
            StaticMemberDTO(
                id=member_id,
                segment_id=segment_id,
                contact_id=contact_id,
                source_type="manual",
                metadata={"source": "test"},
                created_at=now,
                updated_at=now,
                contact=ContactSummaryDTO(
                    id=contact_id,
                    first_name="Denis",
                    last_name=None,
                    middle_name=None,
                    status="active",
                ),
            )
        )

        response = await add_static_member(
            segment_id=segment_id,
            payload=AddStaticMemberRequestSchema(
                contact_id=contact_id,
                source_type="manual",
                metadata={"source": "test"},
            ),
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(use_case.command.tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(use_case.command.segment_id.uuid, segment_id)
        self.assertEqual(use_case.command.contact_id.uuid, contact_id)
        self.assertEqual(response.id, member_id)
        self.assertEqual(response.contact.first_name, "Denis")

    async def test_add_static_member_requires_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await add_static_member(
                segment_id=uuid4(),
                payload=AddStaticMemberRequestSchema(contact_id=uuid4()),
                context=SimpleNamespace(principal=None),
                use_case=_UseCaseStub(),
            )

        self.assertEqual(caught.exception.status_code, 401)

    async def test_add_static_member_maps_contact_not_found_to_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await add_static_member(
                segment_id=uuid4(),
                payload=AddStaticMemberRequestSchema(contact_id=uuid4()),
                context=_context(uuid4()),
                use_case=_UseCaseStub(
                    exc=SegmentStaticMemberContactNotFoundError(str(uuid4()))
                ),
            )

        self.assertEqual(caught.exception.status_code, 404)

    async def test_list_static_members_maps_query_and_response_explicitly(self) -> None:
        tenant_id = uuid4()
        segment_id = uuid4()
        contact_id = uuid4()
        now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
        use_case = _UseCaseStub(
            [
                StaticMemberDTO(
                    id=uuid4(),
                    segment_id=segment_id,
                    contact_id=contact_id,
                    source_type="api",
                    metadata=None,
                    created_at=now,
                    updated_at=now,
                    contact=None,
                )
            ]
        )

        response = await list_static_members(
            segment_id=segment_id,
            context=_context(tenant_id),
            use_case=use_case,
            limit=25,
            offset=5,
            include_contact_summary=False,
        )

        self.assertEqual(use_case.command.tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(use_case.command.segment_id.uuid, segment_id)
        self.assertEqual(use_case.command.limit, 25)
        self.assertFalse(use_case.command.include_contact_summary)
        self.assertEqual(response.count, 1)
        self.assertEqual(response.items[0].contact_id, contact_id)

    async def test_remove_static_member_returns_204_response(self) -> None:
        tenant_id = uuid4()
        segment_id = uuid4()
        contact_id = uuid4()
        use_case = _UseCaseStub(False)

        response = await remove_static_member(
            segment_id=segment_id,
            contact_id=contact_id,
            context=_context(tenant_id),
            use_case=use_case,
        )

        self.assertEqual(use_case.command.tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(use_case.command.segment_id.uuid, segment_id)
        self.assertEqual(use_case.command.contact_id.uuid, contact_id)
        self.assertEqual(response.status_code, 204)


__all__ = ["SegmentationHttpRouterTests"]
