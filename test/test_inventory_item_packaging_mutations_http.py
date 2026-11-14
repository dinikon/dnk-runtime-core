"""Контракты PUT/PATCH упаковки с реальными схемами, handlers, auth и CSRF."""

from dataclasses import replace
from decimal import Decimal, localcontext
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from src.modules.inventory.application.inventory_item.command.add_item_packaging.handler import (
    AddItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.command.add_item_packaging.command import (
    AddItemPackagingCommand,
)
from src.modules.inventory.application.inventory_item.command.update_item_packaging.handler import (
    UpdateItemPackagingHandler,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemConflictError
from test import test_inventory_item_packaging_http as support


class ItemPackagingMutationsHttpTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет раздельные HTTP-контракты полного и частичного изменения."""

    async def asyncSetUp(self) -> None:
        """Переиспользует сборку тестового API и подготавливает сохранённую упаковку."""
        await support.ItemPackagingHttpTests.asyncSetUp(self)
        await AddItemPackagingHandler(
            self.items, self.types, self.app.state.uuid_generator
        ).execute(
            AddItemPackagingCommand(
                self.item.id, self.kind.id, "BOX-12", "Ящик", Decimal(12), "PCS"
            )
        )
        self.item = self.items.save.await_args.args[0]
        self.items.get_for_update.return_value = self.item
        self.items.save.reset_mock()
        self.url += f"/{self.identifier}"
        self.payload = {
            "packaging_type_id": str(self.kind.id.uuid),
            "code": "BOX-24",
            "name": " Ящик 24 ",
            "content_quantity": "24",
            "content_uom": "PCS",
        }

    async def test_put_and_individual_patch_fields_return_complete_contracts(
        self,
    ) -> None:
        """PUT меняет все поля, PATCH каждого поля сохраняет значения остальных."""
        response = await self.client.put(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "id": str(self.identifier),
                "inventory_item_id": str(self.item.id.uuid),
                "packaging_type_id": str(self.kind.id.uuid),
                "code": "BOX-24",
                "name": "Ящик 24",
                "content_quantity": "24",
                "content_uom": "PCS",
            },
        )
        for payload in (
            {"code": "NewCASE"},
            {"name": "Новое имя"},
            {"content_quantity": "36"},
            {"content_uom": "PCS"},
            {"packaging_type_id": str(self.kind.id.uuid)},
        ):
            response = await self.client.patch(
                self.url, headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 200, response.text)
            for key, value in payload.items():
                self.assertEqual(response.json()[key], value)
            self.assertEqual(response.json()["id"], str(self.identifier))
        path = (
            "/api/console/inventory/items/{inventory_item_id}/packagings/{packaging_id}"
        )
        schema = self.app.openapi()
        self.assertEqual(set(schema["paths"][path]), {"get", "put", "patch", "delete"})
        for method, name in [
            ("put", "PutItemPackagingResponse"),
            ("patch", "PatchItemPackagingResponse"),
        ]:
            self.assertEqual(
                schema["paths"][path][method]["responses"]["200"]["content"][
                    "application/json"
                ]["schema"]["$ref"],
                f"#/components/schemas/{name}",
            )
        request = schema["components"]["schemas"]["PutItemPackagingRequest"]
        self.assertEqual(set(request["required"]), set(self.payload))
        self.assertEqual(request["properties"]["content_quantity"]["type"], "string")

    async def test_invalid_shapes_never_enter_handler(self) -> None:
        """Разделяет обязательный PUT и непустой PATCH без null, readonly и нестрогих значений."""
        common = [
            *({field: None} for field in self.payload),
            *(
                {"content_quantity": v}
                for v in [0, 1.5, True, "NaN", "Infinity", "-Infinity", "bad"]
            ),
            {"code": 1},
            {"name": False},
            {"content_uom": 1},
            {"packaging_type_id": "bad"},
            *(
                {key: value}
                for key, value in [
                    ("id", str(uuid4())),
                    ("inventory_item_id", str(uuid4())),
                    ("position", 1),
                    ("version", 1),
                    ("is_active", False),
                    ("unknown", 1),
                ]
            ),
        ]
        with patch.object(
            UpdateItemPackagingHandler, "execute", new_callable=AsyncMock
        ) as execute:
            for method in ("PUT", "PATCH"):
                invalid = (
                    [{}, *common]
                    if method == "PATCH"
                    else [
                        {},
                        *(
                            {k: v for k, v in self.payload.items() if k != field}
                            for field in self.payload
                        ),
                        *({**self.payload, **changes} for changes in common),
                    ]
                )
                for payload in invalid:
                    with self.subTest(method=method, payload=payload):
                        response = await self.client.request(
                            method, self.url, headers=self.headers, json=payload
                        )
                        self.assertEqual(response.status_code, 422, response.text)
            execute.assert_not_awaited()
        self.items.save.assert_not_awaited()

    async def test_patch_parsing_keeps_zero_for_domain_and_decimal_context(
        self,
    ) -> None:
        """Ноль доходит до Domain и отклоняется, большие Decimal не округляются при разборе."""
        response = await self.client.patch(
            self.url, headers=self.headers, json={"content_quantity": "0"}
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.items.save.assert_not_awaited()
        value = "12345678901234567890123456789012345678901234567890"
        with localcontext() as context:
            context.prec = 4
            response = await self.client.patch(
                self.url, headers=self.headers, json={"content_quantity": value}
            )
            self.assertEqual(context.prec, 4)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(Decimal(response.json()["content_quantity"]), Decimal(value))

    async def test_domain_statuses_and_readonly_identity(self) -> None:
        """Переводит конфликты и отсутствующие корни, не заменяя существующую Entity."""
        for payload in (
            {"code": " "},
            {"name": "\u200bName"},
            {"content_quantity": "-1"},
            {"content_quantity": "0.5"},
            {"content_uom": "KG"},
            {"content_uom": "UNKNOWN"},
        ):
            response = await self.client.patch(
                self.url, headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 422, response.text)
        for method in ("PUT", "PATCH"):
            payload = self.payload if method == "PUT" else {"name": "Новое"}
            self.types.get_for_update.return_value = self.kind.deactivate()
            self.assertEqual(
                (
                    await self.client.request(
                        method, self.url, headers=self.headers, json=payload
                    )
                ).status_code,
                409,
            )
            self.types.get_for_update.return_value = None
            self.assertEqual(
                (
                    await self.client.request(
                        method, self.url, headers=self.headers, json=payload
                    )
                ).status_code,
                404,
            )
            self.types.get_for_update.return_value = self.kind
            self.items.save.side_effect = InventoryItemConflictError("code conflict")
            self.assertEqual(
                (
                    await self.client.request(
                        method, self.url, headers=self.headers, json=payload
                    )
                ).status_code,
                409,
            )
            self.items.save.side_effect = None
            self.assertEqual(
                (
                    await self.client.request(
                        method,
                        self.url.rsplit("/", 1)[0] + f"/{uuid4()}",
                        headers=self.headers,
                        json=payload,
                    )
                ).status_code,
                404,
            )
            self.items.get_for_update.return_value = None
            self.assertEqual(
                (
                    await self.client.request(
                        method, self.url, headers=self.headers, json=payload
                    )
                ).status_code,
                404,
            )
            self.items.get_for_update.return_value = self.item

    async def test_auth_tenant_csrf_and_both_path_identifiers(self) -> None:
        """Оба метода проверяют auth/tenant/CSRF и UUID до обращения к Domain."""
        self.items.get_for_update.reset_mock()
        for method in ("PUT", "PATCH"):
            payload = self.payload if method == "PUT" else {"name": "Новое"}
            self.assertEqual(
                (await self.client.request(method, self.url, json=payload)).status_code,
                403,
            )
            for principal, status in (
                (None, 401),
                (replace(self.context.principal, tenant_id=None), 403),
            ):
                self.app.state.test_context = replace(self.context, principal=principal)
                response = await self.client.request(
                    method, self.url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, status, response.text)
            self.app.state.test_context = self.context
            for path in (
                self.url.rsplit("/", 1)[0] + "/bad",
                "/api/console/inventory/items/bad/packagings/" + str(self.identifier),
            ):
                self.assertEqual(
                    (
                        await self.client.request(
                            method, path, headers=self.headers, json=payload
                        )
                    ).status_code,
                    422,
                )
        self.items.get_for_update.assert_not_awaited()
