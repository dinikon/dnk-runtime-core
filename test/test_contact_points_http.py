"""Transport contracts for label endpoints without a database service."""

import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from src.modules.contact_points.application.label.command.create_label.dto import (
    CreateContactPointLabelDTO,
)
from src.modules.contact_points.application.label.command.update_label.dto import (
    UpdateContactPointLabelDTO,
)
from src.modules.contact_points.application.label.query.list_labels.dto import (
    ListContactPointLabelDTO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.presentation.label.depends import (
    get_create_label_handler,
    get_list_labels_handler,
    get_update_label_handler,
)
from src.modules.contact_points.presentation.label.router import router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.shared.presentation.uuid.depends import get_uuid_generator


class ContactPointLabelHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/console")
        self.user_id, self.tenant_id, self.label_id = uuid4(), uuid4(), uuid4()
        self.context = RequestContext(
            Principal(str(self.user_id), str(self.tenant_id), "session", ("admin",)),
            None,
            None,
            None,
        )
        self.app.dependency_overrides[require_authenticated_request_context] = (
            lambda: self.context
        )
        self.app.dependency_overrides[require_csrf] = lambda: None
        self.app.dependency_overrides[get_uuid_generator] = lambda: Mock(
            new=Mock(return_value=self.label_id)
        )
        self.create = Mock(
            execute=AsyncMock(
                return_value=CreateContactPointLabelDTO(
                    ContactPointLabelIdVO(self.label_id),
                    ContactPointType.EMAIL,
                    "Рабочий",
                    True,
                )
            )
        )
        self.update = Mock(
            execute=AsyncMock(
                return_value=UpdateContactPointLabelDTO(
                    ContactPointLabelIdVO(self.label_id),
                    ContactPointType.EMAIL,
                    "Личный",
                    False,
                )
            )
        )
        self.list = Mock(
            execute=AsyncMock(
                return_value=(
                    ListContactPointLabelDTO(
                        ContactPointLabelIdVO(self.label_id),
                        ContactPointType.EMAIL,
                        "Рабочий",
                        True,
                    ),
                )
            )
        )
        self.app.dependency_overrides[get_create_label_handler] = lambda: self.create
        self.app.dependency_overrides[get_update_label_handler] = lambda: self.update
        self.app.dependency_overrides[get_list_labels_handler] = lambda: self.list

    async def test_list_create_update_keep_http_payloads(self):
        async with AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://test"
        ) as client:
            listed = await client.get("/api/console/contact-points/labels?type=email")
            created = await client.post(
                "/api/console/contact-points/labels",
                json={"type": "email", "name": "Рабочий"},
            )
            updated = await client.patch(
                f"/api/console/contact-points/labels/{self.label_id}",
                json={"name": "Личный", "is_active": False},
            )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            listed.json(),
            [
                {
                    "id": str(self.label_id),
                    "type": "email",
                    "name": "Рабочий",
                    "is_active": True,
                }
            ],
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json(), listed.json()[0])
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Личный")
        self.assertFalse(updated.json()["is_active"])
        self.assertEqual(
            self.create.execute.await_args.args[0].tenant_id.uuid, self.tenant_id
        )
        self.assertEqual(
            self.update.execute.await_args.args[0].actor_id.uuid, self.user_id
        )

    async def test_validation_and_access_rules(self):
        async with AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://test"
        ) as client:
            invalid = await client.patch(
                f"/api/console/contact-points/labels/{self.label_id}",
                json={"name": None},
            )
            extra = await client.post(
                "/api/console/contact-points/labels",
                json={
                    "type": "email",
                    "name": "Рабочий",
                    "tenant_id": str(self.tenant_id),
                },
            )
            self.app.dependency_overrides[require_authenticated_request_context] = (
                lambda: RequestContext(
                    Principal(
                        str(self.user_id), str(self.tenant_id), "session", ("member",)
                    ),
                    None,
                    None,
                    None,
                )
            )
            denied = await client.post(
                "/api/console/contact-points/labels",
                json={"type": "email", "name": "Рабочий"},
            )
            self.app.dependency_overrides[require_authenticated_request_context] = (
                lambda: RequestContext(
                    Principal(str(self.user_id), None, "session", ("admin",)),
                    None,
                    None,
                    None,
                )
            )
            no_tenant = await client.get("/api/console/contact-points/labels")

            def unauthorized():
                raise HTTPException(401, "Authentication required.")

            self.app.dependency_overrides[require_authenticated_request_context] = (
                unauthorized
            )
            no_auth = await client.get("/api/console/contact-points/labels")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(extra.status_code, 422)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(no_tenant.status_code, 403)
        self.assertEqual(no_auth.status_code, 401)
