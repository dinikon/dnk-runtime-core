import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from src.modules.crm.application.company.dto import CompanyDTO, CompanyPageDTO
from src.modules.crm.application.contact.dto import ContactDTO, ContactPageDTO
from src.modules.crm.domain.company import CompanyNotFoundError
from src.modules.crm.domain.contact import InvalidContactNameError
from src.modules.crm.presentation.depends.application import (
    get_create_company_use_case,
    get_create_contact_use_case,
    get_delete_company_use_case,
    get_delete_contact_use_case,
    get_get_company_use_case,
    get_get_contact_use_case,
    get_list_companies_use_case,
    get_list_contacts_use_case,
    get_update_company_use_case,
    get_update_contact_use_case,
)
from src.modules.crm.presentation.http.router import router
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.identity.presentation.http.csrf import issue_csrf
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.domain.identity_context import Principal, RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.tokens import InMemoryTokenBackend
from src.modules.shared.presentation.identity_context.depends import (
    require_authenticated_request_context,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.shared.presentation.uuid.depends import get_uuid_generator


class CrmHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant_uuid = uuid4()
        self.user_uuid = uuid4()
        self.contact_uuid = uuid4()
        self.company_uuid = uuid4()
        self.now = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)
        tenant_id = EntityIdVO.from_value(self.tenant_uuid)
        user_id = EntityIdVO.from_value(self.user_uuid)
        self.contact = ContactDTO(
            id=ContactIdVO.from_value(self.contact_uuid),
            first_name="Іван",
            last_name="Петренко",
            middle_name=None,
            created_at=self.now,
            updated_at=self.now,
            created_by=user_id,
            updated_by=user_id,
        )
        self.company = CompanyDTO(
            id=CompanyIdVO.from_value(self.company_uuid),
            name="Acme",
            created_at=self.now,
            updated_at=self.now,
            created_by=user_id,
            updated_by=user_id,
        )
        self.use_cases = {
            get_create_contact_use_case: AsyncMock(return_value=self.contact),
            get_get_contact_use_case: AsyncMock(return_value=self.contact),
            get_list_contacts_use_case: AsyncMock(
                return_value=ContactPageDTO((self.contact,), 1, 25, 0)
            ),
            get_update_contact_use_case: AsyncMock(return_value=self.contact),
            get_delete_contact_use_case: AsyncMock(return_value=None),
            get_create_company_use_case: AsyncMock(return_value=self.company),
            get_get_company_use_case: AsyncMock(return_value=self.company),
            get_list_companies_use_case: AsyncMock(
                return_value=CompanyPageDTO((self.company,), 1, 25, 0)
            ),
            get_update_company_use_case: AsyncMock(return_value=self.company),
            get_delete_company_use_case: AsyncMock(return_value=None),
        }
        self.context = RequestContext(
            principal=Principal(
                user_id=str(self.user_uuid),
                tenant_id=str(self.tenant_uuid),
                session_id="session",
                roles=("member",),
            ),
            request_id=None,
            ip=None,
            user_agent=None,
        )
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/console")
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())

        @self.app.get("/csrf")
        async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
            return await issue_csrf(request, response, tokens)

        self.app.dependency_overrides[require_authenticated_request_context] = (
            lambda: self.context
        )
        self.app.dependency_overrides[get_uuid_generator] = lambda: type(
            "Generator", (), {"new": lambda _: self.contact_uuid}
        )()

        def provider(value):
            def dependency():
                return value

            return dependency

        for dependency, use_case in self.use_cases.items():
            self.app.dependency_overrides[dependency] = provider(use_case)
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://tenant.example",
        )
        csrf = await self.client.get("/csrf")
        self.headers = {
            "Origin": "https://tenant.example",
            "X-CSRF-Token": csrf.json()["csrf_token"],
        }

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_contact_crud_search_pagination_and_trusted_tenant(self):
        response = await self.client.get(
            "/api/console/crm/contacts?q=Петренко&limit=25&offset=0"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        query = self.use_cases[get_list_contacts_use_case].await_args.args[0]
        self.assertEqual(query.tenant_id.uuid, self.tenant_uuid)
        self.assertEqual(query.q, "Петренко")

        response = await self.client.post(
            "/api/console/crm/contacts",
            json={"first_name": "Іван"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        command = self.use_cases[get_create_contact_use_case].await_args.args[0]
        self.assertEqual(command.tenant_id.uuid, self.tenant_uuid)
        self.assertEqual(command.actor_id.uuid, self.user_uuid)

        response = await self.client.put(
            f"/api/console/crm/contacts/{self.contact_uuid}",
            json={"first_name": "Іван", "last_name": "Петренко"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.get(
            f"/api/console/crm/contacts/{self.contact_uuid}"
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.delete(
            f"/api/console/crm/contacts/{self.contact_uuid}",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 204, response.text)

        response = await self.client.post(
            "/api/console/crm/contacts",
            json={"first_name": "Іван", "tenant_id": str(uuid4())},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 422, response.text)

    async def test_company_crud_and_csrf(self):
        response = await self.client.get("/api/console/crm/companies?q=Acme")
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.post(
            "/api/console/crm/companies", json={"name": "Acme"}
        )
        self.assertEqual(response.status_code, 403, response.text)
        response = await self.client.post(
            "/api/console/crm/companies",
            json={"name": "Acme"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        response = await self.client.put(
            f"/api/console/crm/companies/{self.company_uuid}",
            json={"name": "Acme Group"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.delete(
            f"/api/console/crm/companies/{self.company_uuid}",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 204, response.text)

    async def test_unauthenticated_request_is_rejected(self):
        async def unauthorized():
            raise HTTPException(401, "Unauthorized.")

        self.app.dependency_overrides[require_authenticated_request_context] = (
            unauthorized
        )
        response = await self.client.get("/api/console/crm/contacts")
        self.assertEqual(response.status_code, 401, response.text)

    async def test_domain_validation_and_not_found_are_mapped(self):
        self.use_cases[get_create_contact_use_case].side_effect = (
            InvalidContactNameError("First name must not be empty.")
        )
        response = await self.client.post(
            "/api/console/crm/contacts",
            json={"first_name": "   "},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 422, response.text)

        self.use_cases[get_get_company_use_case].side_effect = CompanyNotFoundError(
            "Company not found."
        )
        response = await self.client.get(
            f"/api/console/crm/companies/{self.company_uuid}"
        )
        self.assertEqual(response.status_code, 404, response.text)

    async def test_persistence_conflict_and_invalid_pagination_are_mapped(self):
        self.use_cases[get_create_company_use_case].side_effect = IntegrityError(
            "insert", {}, RuntimeError("conflict")
        )
        response = await self.client.post(
            "/api/console/crm/companies",
            json={"name": "Acme"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 409, response.text)

        response = await self.client.get("/api/console/crm/companies?limit=101")
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
