"""HTTP-контракты типов тары с настоящими Pydantic, auth, CSRF и Domain."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.packaging_type.command.create_packaging_type.handler import (
    CreatePackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.handler import (
    GetPackagingTypeHandler,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.dto import (
    GetPackagingTypeResultDTO,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.handler import (
    ListPackagingTypesHandler,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.dto import (
    ListPackagingTypesResultDTO,
)
from src.modules.inventory.domain.packaging_type.error import (
    PackagingTypeCodeAlreadyExistsError,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    get_create_packaging_type_handler,
    get_get_packaging_type_handler,
    get_list_packaging_types_handler,
)
from src.modules.inventory.presentation.packaging_type.router import router
from test.inventory_item_support import inventory_item_app


class PackagingTypeHttpTests(unittest.IsolatedAsyncioTestCase):
    """Разделяет проверку структуры запроса и предметные отказы Domain."""

    async def asyncSetUp(self) -> None:
        """Собирает реальные handlers на тестовых портах с auth и CSRF."""
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.identifier = uuid4()
        self.write = Mock(add=AsyncMock())
        self.read = Mock(
            get_details=AsyncMock(
                return_value=GetPackagingTypeResultDTO(
                    self.identifier, "BOX", "Ящик", False
                )
            ),
            list=AsyncMock(return_value=ListPackagingTypesResultDTO((), 0, 0, 50)),
        )
        create = CreatePackagingTypeHandler(
            self.write, Mock(new=Mock(return_value=self.identifier))
        )
        self.create_handler = Mock(execute=AsyncMock(wraps=create.execute))
        get = GetPackagingTypeHandler(self.read)
        self.get_handler = Mock(execute=AsyncMock(wraps=get.execute))
        listing = ListPackagingTypesHandler(self.read)
        self.list_handler = Mock(execute=AsyncMock(wraps=listing.execute))
        self.app = inventory_item_app(Mock(), self.context)
        self.app.include_router(router, prefix="/api/console")
        self.app.dependency_overrides[get_create_packaging_type_handler] = (
            lambda: self.create_handler
        )
        self.app.dependency_overrides[get_get_packaging_type_handler] = (
            lambda: self.get_handler
        )
        self.app.dependency_overrides[get_list_packaging_types_handler] = (
            lambda: self.list_handler
        )
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.url = "/api/console/inventory/packaging-types"
        self.payload = {"code": " BOX ", "name": " Ящик "}

    async def test_create_and_get_have_specific_response_contracts(self) -> None:
        """POST задаёт Domain defaults, GET сохраняет false, методы имеют разные схемы."""
        created = await self.client.post(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(
            created.json(),
            {
                "id": str(self.identifier),
                "code": "BOX",
                "name": "Ящик",
                "is_active": True,
            },
        )
        fetched = await self.client.get(f"{self.url}/{self.identifier}")
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertFalse(fetched.json()["is_active"])
        paths = self.app.openapi()["paths"]
        for path, method, status, schema in (
            (self.url, "post", "201", "CreatePackagingTypeResponse"),
            (
                f"{self.url}/{{packaging_type_id}}",
                "get",
                "200",
                "GetPackagingTypeResponse",
            ),
            (self.url, "get", "200", "ListPackagingTypesResponse"),
        ):
            self.assertEqual(
                paths[path][method]["responses"][status]["content"]["application/json"][
                    "schema"
                ]["$ref"],
                f"#/components/schemas/{schema}",
            )

    async def test_create_rejects_structure_before_handler(self) -> None:
        """Строгие строки, обязательные поля и запрет неизвестных полей принадлежат Pydantic."""
        for payload in (
            {},
            {"code": "BOX"},
            {"name": "Ящик"},
            {**self.payload, "code": None},
            {**self.payload, "name": None},
            {**self.payload, "code": 1},
            {**self.payload, "name": False},
            {**self.payload, "id": str(uuid4())},
            {**self.payload, "is_active": False},
            {**self.payload, "allowed_uoms": ["PCS"]},
        ):
            with self.subTest(payload=payload):
                response = await self.client.post(
                    self.url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.create_handler.execute.assert_not_awaited()
        self.write.add.assert_not_awaited()

    async def test_domain_and_conflict_and_missing_statuses(self) -> None:
        """Различает структурно корректное плохое значение, занятый код и отсутствие карточки."""
        for payload in (
            {"code": " ", "name": "Name"},
            {"code": "BOX", "name": "Bad\u200bName"},
        ):
            response = await self.client.post(
                self.url, headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.write.add.side_effect = PackagingTypeCodeAlreadyExistsError("occupied")
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            409,
        )
        self.read.get_details.return_value = None
        self.assertEqual(
            (await self.client.get(f"{self.url}/{uuid4()}")).status_code, 404
        )
        self.assertEqual((await self.client.get(f"{self.url}/bad")).status_code, 422)

    async def test_list_preserves_false_and_rejects_invalid_parameters_before_handler(
        self,
    ) -> None:
        """Передаёт false, trim поиска и границы пагинации в конкретную Query."""
        response = await self.client.get(
            self.url,
            params={
                "search": " ЯЩИК%_ ",
                "is_active": "false",
                "offset": 20,
                "limit": 20,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        query = self.read.list.await_args.args[0]
        self.assertEqual(
            (query.search, query.is_active, query.offset, query.limit),
            ("ЯЩИК%_", False, 20, 20),
        )
        self.list_handler.execute.reset_mock()
        for params in (
            {"offset": -1},
            {"offset": 2_147_483_648},
            {"limit": 0},
            {"limit": 101},
            {"is_active": "bad"},
            {"unknown": "x"},
        ):
            with self.subTest(params=params):
                response = await self.client.get(self.url, params=params)
                self.assertEqual(response.status_code, 422, response.text)
        self.list_handler.execute.assert_not_awaited()

    async def test_security_rejects_before_handlers(self) -> None:
        """Требует principal и tenant во всех методах и CSRF/Origin для POST."""
        for headers in (
            {},
            {**self.headers, "X-CSRF-Token": "bad"},
            {**self.headers, "Origin": "https://other.example"},
        ):
            self.assertEqual(
                (
                    await self.client.post(self.url, headers=headers, json=self.payload)
                ).status_code,
                403,
            )
        for principal, expected in (
            (None, 401),
            (replace(self.context.principal, tenant_id=None), 403),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            for method, url, payload in (
                ("GET", self.url, None),
                ("GET", f"{self.url}/{self.identifier}", None),
                ("POST", self.url, self.payload),
            ):
                response = await self.client.request(
                    method, url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, expected, response.text)
        for handler in (self.create_handler, self.get_handler, self.list_handler):
            handler.execute.assert_not_awaited()
