"""DELETE PackagingType: настоящий controller, Domain, auth/CSRF и пустой HTTP-ответ."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.packaging_type.command.delete_packaging_type.handler import (
    DeletePackagingTypeHandler,
)
from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.deletion_usage import (
    PackagingTypeDeletionUsage,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeInUseError
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.presentation.packaging_type.depends import (
    get_delete_packaging_type_handler,
)
from src.modules.inventory.presentation.packaging_type.router import router
from test.inventory_item_support import inventory_item_app


class PackagingTypeDeleteHttpTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет маршрутизацию и статусы с реальной бизнес-проверкой через тестовые порты."""

    async def asyncSetUp(self) -> None:
        """Собирает авторизованное HTTP-приложение и выдаёт настоящий CSRF-токен."""
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.kind = PackagingType.create(
            identifier=PackagingTypeIdVO(uuid4()),
            code=PackagingCodeVO("BOX"),
            name=PackagingNameVO("Ящик"),
        )
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.kind), delete=AsyncMock()
        )
        self.usage = Mock(get=AsyncMock(return_value=PackagingTypeDeletionUsage(False)))
        real = DeletePackagingTypeHandler(self.repository, self.usage)
        self.handler = Mock(execute=AsyncMock(wraps=real.execute))
        self.app = inventory_item_app(Mock(), self.context)
        self.app.include_router(router, prefix="/api/console")
        self.app.dependency_overrides[get_delete_packaging_type_handler] = (
            lambda: self.handler
        )
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.url = f"/api/console/inventory/packaging-types/{self.kind.id.uuid}"

    async def test_unused_active_and_inactive_return_empty_204(self) -> None:
        """Пустая операция не возвращает JSON или Content-Type и не требует тела запроса."""
        for kind in (self.kind, self.kind.deactivate()):
            self.repository.get_for_update.return_value = kind
            response = await self.client.delete(self.url, headers=self.headers)
            self.assertEqual(response.status_code, 204, response.text)
            self.assertEqual(response.content, b"")
            self.assertNotIn("content-type", response.headers)
            self.assertEqual(
                self.handler.execute.await_args.args[0].packaging_type_id, kind.id
            )

    async def test_used_type_returns_409_before_repository_delete(self) -> None:
        """Наличие любой ссылки запрещает удаление в обоих состояниях активности."""
        self.usage.get.return_value = PackagingTypeDeletionUsage(True)
        for kind in (self.kind, self.kind.deactivate()):
            self.repository.get_for_update.return_value = kind
            response = await self.client.delete(self.url, headers=self.headers)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertIn("деактивировать", response.json()["detail"])
        self.repository.delete.assert_not_awaited()

    async def test_missing_root_returns_404_without_usage_read(self) -> None:
        """Отсутствующий корень и повторное удаление используют один контракт 404."""
        self.repository.get_for_update.return_value = None
        response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 404, response.text)
        self.usage.get.assert_not_awaited()
        self.repository.delete.assert_not_awaited()

    async def test_defensive_fk_conflict_and_unexpected_failure_are_not_success(
        self,
    ) -> None:
        """Защитная предметная ошибка даёт 409, неожиданная ошибка порта — 500."""
        for error, expected in (
            (PackagingTypeInUseError("used"), 409),
            (RuntimeError("database unavailable"), 500),
        ):
            self.repository.delete.side_effect = error
            response = await self.client.delete(self.url, headers=self.headers)
            self.assertEqual(response.status_code, expected, response.text)

    async def test_invalid_uuid_is_rejected_before_handler(self) -> None:
        """UUID проверяется Presentation до чтения или попытки удаления."""
        response = await self.client.delete(
            "/api/console/inventory/packaging-types/not-a-uuid", headers=self.headers
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.handler.execute.assert_not_awaited()

    async def test_authentication_tenant_origin_and_csrf_are_required(self) -> None:
        """Неавторизованный контекст и неверный CSRF не достигают сценария записи."""
        for principal, expected in (
            (None, 401),
            (Principal(str(uuid4()), None, "session", ("member",)), 403),
            (
                Principal(
                    str(uuid4()),
                    str(uuid4()),
                    "session",
                    ("member",),
                    is_authenticated=False,
                ),
                401,
            ),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            response = await self.client.delete(self.url, headers=self.headers)
            self.assertEqual(response.status_code, expected, response.text)
        self.app.state.test_context = self.context
        for headers in (
            {},
            {"Origin": self.origin},
            {**self.headers, "X-CSRF-Token": "invalid"},
            {**self.headers, "Origin": "https://outside.example"},
        ):
            response = await self.client.delete(self.url, headers=headers)
            self.assertEqual(response.status_code, 403, response.text)
        self.handler.execute.assert_not_awaited()
        self.repository.delete.assert_not_awaited()

    async def test_openapi_has_no_request_or_response_body(self) -> None:
        """DELETE не создаёт фиктивные request/response-схемы для пустой операции."""
        operation = self.app.openapi()["paths"][
            "/api/console/inventory/packaging-types/{packaging_type_id}"
        ]["delete"]
        self.assertNotIn("requestBody", operation)
        self.assertNotIn("content", operation["responses"]["204"])
