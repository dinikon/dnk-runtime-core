"""CRM владеет target; ContactPoints обслуживает значения и связи."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.crm.application.contact_point.dto import (
    ContactPointDraftDTO,
    ContactPointDTO,
    ContactPointsDTO,
)
from src.modules.crm.presentation.company.depends import (
    get_company_query_repository,
    get_company_repository,
)
from src.modules.crm.presentation.company.router import router as company_router
from src.modules.crm.presentation.contact.depends import (
    get_contact_query_repository,
    get_contact_repository,
)
from src.modules.crm.presentation.depends.contact_points import (
    get_company_contact_points,
    get_contact_contact_points,
)
from src.modules.crm.infrastructure.contact_point.adapter import ContactPointsAdapter
from src.modules.contact_points.application.query.get_targets_contact_points.dto import (
    ContactPointBindingDTO,
)
from src.modules.contact_points.domain.value_object.binding_identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.binding_error import (
    InvalidContactPointBindingError,
)
from src.modules.contact_points.domain.value_object.contact_point_identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.value_object.value import (
    ContactPointType,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.presentation.persistence.depends import UoWDep
from test.crm_contact_support import contact_app


class ContactPointsAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_owner_drafts_and_result_without_orm(self):
        tenant, actor, owner = (EntityIdVO(uuid4()) for _ in range(3))
        existing_binding, label = uuid4(), uuid4()
        row = ContactPointBindingDTO(
            target=Mock(),
            binding_id=ContactPointBindingIdVO(existing_binding),
            contact_point_id=ContactPointIdVO(uuid4()),
            type=ContactPointType.EMAIL,
            value="Name@example.com",
            country_code=None,
            label_id=None,
            position=0,
        )
        reader = Mock(execute=AsyncMock(return_value=(row,)))
        writer = Mock(execute=AsyncMock())
        remover = Mock(execute=AsyncMock())
        adapter = ContactPointsAdapter(
            "crm.company",
            reader,
            writer,
            remover,
            Mock(new=Mock(side_effect=[uuid4(), uuid4()])),
        )
        await adapter.sync(
            tenant,
            actor,
            owner,
            None,
            (ContactPointDraftDTO("Name@Example.COM", existing_binding, label),),
        )
        command = writer.execute.await_args.args[0]
        self.assertEqual(command.target.model_key, "crm.company")
        self.assertEqual(command.target.record_id, owner)
        self.assertEqual(command.tenant_id, tenant)
        self.assertEqual(command.actor_id, actor)
        self.assertIsNone(command.phones)
        self.assertEqual(command.emails[0].binding_id.uuid, existing_binding)
        self.assertEqual(command.emails[0].label_id.uuid, label)
        listed = await adapter.list(tenant, owner)
        self.assertEqual(listed.phones, ())
        self.assertEqual(listed.emails[0].value, "Name@example.com")
        self.assertEqual(
            reader.execute.await_args.args[0].targets[0].model_key,
            "crm.company",
        )
        await adapter.remove(tenant, owner)
        self.assertEqual(
            remover.execute.await_args.args[0].target.model_key,
            "crm.company",
        )


class CrmContactPointsHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor = uuid4(), uuid4()
        self.contact_id, self.company_id = uuid4(), uuid4()
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.session = SimpleNamespace(
            commit=AsyncMock(), rollback=AsyncMock(), close=AsyncMock()
        )
        self.app = contact_app(lambda: self.session, self.context)
        self.app.include_router(company_router, prefix="/api/console")
        self.contact_repo = Mock(
            get_for_update=AsyncMock(return_value=object()), delete=AsyncMock()
        )
        self.company_repo = Mock(
            get_for_update=AsyncMock(return_value=object()), delete=AsyncMock()
        )
        self.contact_query = Mock(get_details=AsyncMock(return_value=object()))
        self.company_query = Mock(get_details=AsyncMock(return_value=object()))
        point = ContactPointDTO(
            uuid4(), uuid4(), "phone", "+380501234567", "UA", None, 0
        )
        self.contact_points = Mock(
            list=AsyncMock(return_value=ContactPointsDTO((point,), ())),
            sync=AsyncMock(),
            remove=AsyncMock(),
        )
        self.company_points = Mock(
            list=AsyncMock(return_value=ContactPointsDTO((), ())),
            sync=AsyncMock(),
            remove=AsyncMock(),
        )

        def contact_repository(uow: UoWDep):
            return self.contact_repo

        def company_repository(uow: UoWDep):
            return self.company_repo

        self.app.dependency_overrides[get_contact_repository] = contact_repository
        self.app.dependency_overrides[get_company_repository] = company_repository
        self.app.dependency_overrides[get_contact_query_repository] = (
            lambda: self.contact_query
        )
        self.app.dependency_overrides[get_company_query_repository] = (
            lambda: self.company_query
        )
        self.app.dependency_overrides[get_contact_contact_points] = (
            lambda: self.contact_points
        )
        self.app.dependency_overrides[get_company_contact_points] = (
            lambda: self.company_points
        )
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.contact_url = f"/api/console/crm/contacts/{self.contact_id}/contact-points"
        self.company_url = (
            f"/api/console/crm/companies/{self.company_id}/contact-points"
        )
        self.session.commit.reset_mock()

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_read_both_owners_and_missing_owner(self):
        contact = await self.client.get(self.contact_url)
        self.assertEqual(contact.status_code, 200, contact.text)
        self.assertEqual(contact.json()["phones"][0]["value"], "+380501234567")
        self.assertEqual(contact.json()["emails"], [])
        self.contact_points.list.assert_awaited_once_with(
            EntityIdVO(self.tenant), self.contact_id_vo()
        )
        company = await self.client.get(self.company_url)
        self.assertEqual(company.status_code, 200, company.text)
        self.assertEqual(company.json(), {"phones": [], "emails": []})
        self.company_query.get_details.return_value = None
        self.company_points.list.reset_mock()
        missing = await self.client.get(self.company_url)
        self.assertEqual(missing.status_code, 404)
        self.company_points.list.assert_not_awaited()

    def contact_id_vo(self):
        from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO

        return ContactIdVO(self.contact_id)

    async def test_put_patch_and_delete_use_owner_and_same_uow(self):
        put = await self.client.put(
            self.contact_url,
            headers=self.headers,
            json={
                "phones": [{"value": "050 123 45 67", "country_code": "UA"}],
                "emails": [],
            },
        )
        self.assertEqual(put.status_code, 200, put.text)
        self.contact_repo.get_for_update.assert_awaited_once()
        args = self.contact_points.sync.await_args.args
        self.assertEqual(
            args[:3],
            (EntityIdVO(self.tenant), EntityIdVO(self.actor), self.contact_id_vo()),
        )
        self.assertEqual(args[3][0].value, "050 123 45 67")
        self.assertEqual(args[4], ())
        patch = await self.client.patch(
            self.company_url, headers=self.headers, json={"emails": []}
        )
        self.assertEqual(patch.status_code, 200, patch.text)
        self.assertIsNone(self.company_points.sync.await_args.args[3])
        self.assertEqual(self.company_points.sync.await_args.args[4], ())
        deleted = await self.client.delete(
            f"/api/console/crm/contacts/{self.contact_id}", headers=self.headers
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.contact_points.remove.assert_awaited_once_with(
            EntityIdVO(self.tenant), self.contact_id_vo()
        )
        self.contact_repo.delete.assert_awaited_once()
        self.session.commit.assert_awaited()

    async def test_auth_csrf_validation_and_missing_owner(self):
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(self.contact_url)).status_code, 401)
        self.app.state.test_context = self.context
        self.assertEqual(
            (await self.client.put(self.contact_url, json={})).status_code, 403
        )
        for method, url, body in (
            ("put", self.contact_url, {"phones": []}),
            (
                "put",
                self.contact_url,
                {"phones": [], "emails": [], "actor_id": str(self.actor)},
            ),
            ("patch", self.company_url, {"phones": None}),
        ):
            response = await getattr(self.client, method)(
                url, headers=self.headers, json=body
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.contact_repo.get_for_update.return_value = None
        missing = await self.client.put(
            self.contact_url, headers=self.headers, json={"phones": [], "emails": []}
        )
        self.assertEqual(missing.status_code, 404, missing.text)
        self.contact_points.sync.assert_not_awaited()

    async def test_commit_failure_is_not_success(self):
        self.session.commit.side_effect = RuntimeError("commit failed")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.put(
                self.contact_url,
                headers=self.headers,
                json={"phones": [], "emails": []},
            )
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()

    async def test_indexed_validation_error_rolls_back(self):
        self.contact_points.sync.side_effect = InvalidContactPointBindingError(
            "Invalid phone", "phones", 0, "value"
        )
        response = await self.client.put(
            self.contact_url,
            headers=self.headers,
            json={"phones": [{"value": "invalid", "country_code": "UA"}], "emails": []},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"][0]["loc"], ["body", "phones", 0, "value"]
        )
        self.session.rollback.assert_awaited_once()
        self.contact_points.list.assert_not_awaited()
