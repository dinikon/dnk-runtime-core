"""DELETE собственной упаковки: пустой 204, ошибки, UUID и auth/CSRF."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.modules.inventory.application.inventory_item.command.delete_item_packaging.handler import (
    DeleteItemPackagingHandler,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from test import test_inventory_item_packaging_mutations_http as support


class DeleteItemPackagingHttpTests(unittest.IsolatedAsyncioTestCase):
    """Использует настоящий controller, handler и Domain с изолированным write-портом."""

    async def asyncSetUp(self) -> None:
        """Собирает сохранённую упаковку и имитирует обновление состояния write-порта."""
        await support.ItemPackagingMutationsHttpTests.asyncSetUp(self)

        async def persist(item: InventoryItem) -> None:
            """Сохраняет новый агрегат для повторного вызова настоящего handler."""
            self.items.get_for_update.return_value = item

        self.items.save.side_effect = persist

    async def test_delete_returns_empty_204_and_repeat_is_404(self) -> None:
        """Не создаёт DTO/response schema и не удаляет родительский агрегат."""
        response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.content, b"")
        self.assertNotIn("content-type", response.headers)
        self.assertEqual(self.items.get_for_update.return_value.packagings, ())
        self.assertEqual(
            self.items.get_for_update.return_value.barcodes, self.item.barcodes
        )
        self.assertEqual(
            (await self.client.delete(self.url, headers=self.headers)).status_code, 404
        )
        self.items.save.assert_awaited_once()
        path = (
            "/api/console/inventory/items/{inventory_item_id}/packagings/{packaging_id}"
        )
        operation = self.app.openapi()["paths"][path]["delete"]
        self.assertNotIn("requestBody", operation)
        self.assertNotIn("content", operation["responses"]["204"])

    async def test_missing_parent_and_foreign_packaging_are_404(self) -> None:
        """Оба идентификатора проверяются write-сценарием без обращения к типу тары."""
        self.types.get_for_update.reset_mock()
        response = await self.client.delete(
            self.url.rsplit("/", 1)[0] + f"/{uuid4()}", headers=self.headers
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.items.get_for_update.return_value = None
        response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 404, response.text)
        self.items.save.assert_not_awaited()
        self.types.get_for_update.assert_not_awaited()

    async def test_uuid_auth_tenant_and_csrf_precede_handler(self) -> None:
        """Presentation проверяет UUID и защиту запроса до выполнения Application."""
        with patch.object(
            DeleteItemPackagingHandler, "execute", new_callable=AsyncMock
        ) as execute:
            for path in (
                self.url.rsplit("/", 1)[0] + "/bad",
                "/api/console/inventory/items/bad/packagings/" + str(self.identifier),
            ):
                self.assertEqual(
                    (await self.client.delete(path, headers=self.headers)).status_code,
                    422,
                )
            self.assertEqual((await self.client.delete(self.url)).status_code, 403)
            self.assertEqual(
                (
                    await self.client.delete(
                        self.url,
                        headers={**self.headers, "Origin": "https://foreign.example"},
                    )
                ).status_code,
                403,
            )
            for principal, status in (
                (None, 401),
                (replace(self.context.principal, tenant_id=None), 403),
            ):
                self.app.state.test_context = replace(self.context, principal=principal)
                response = await self.client.delete(self.url, headers=self.headers)
                self.assertEqual(response.status_code, status, response.text)
            execute.assert_not_awaited()
