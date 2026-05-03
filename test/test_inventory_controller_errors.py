from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.inventory.application.product.dto import ProductDTO
from src.modules.inventory.domain.category.error import (
    CategoryHierarchyError,
    CategoryNotFoundError,
)
from src.modules.inventory.presentation.http.category.controller.update_category import (
    update_category,
)
from src.modules.inventory.presentation.http.category.requests import (
    UpdateCategoryRequestSchema,
)
from src.modules.inventory.presentation.http.product.controller.create_product import (
    create_product,
)
from src.modules.inventory.presentation.http.product.controller.list_products import (
    list_products,
)
from src.modules.inventory.presentation.http.product.requests import (
    CreateProductRequestSchema,
)
from src.modules.shared import EntityIdVO, Principal, RequestContext


def _context() -> RequestContext:
    return RequestContext(
        principal=Principal(
            user_id=str(uuid4()),
            tenant_id=str(uuid4()),
            session_id=str(uuid4()),
            roles=(),
        ),
        request_id=None,
        ip=None,
        user_agent=None,
    )


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, command):
        raise self._exc


class InventoryControllerErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_product_missing_category_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_product(
                payload=CreateProductRequestSchema(
                    sku="SKU-1",
                    product_name="Running Shoe",
                    category_id=uuid4(),
                ),
                context=_context(),
                use_case=_FailingUseCase(CategoryNotFoundError("category-1")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)

    async def test_update_category_hierarchy_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await update_category(
                category_id=uuid4(),
                payload=UpdateCategoryRequestSchema(
                    name="Running",
                    parent_category_id=uuid4(),
                ),
                context=_context(),
                use_case=_FailingUseCase(
                    CategoryHierarchyError("Product category tree cycle detected.")
                ),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_list_products_passes_category_filter_to_query(self) -> None:
        category_id = uuid4()
        now = datetime.now(UTC)
        recorded_query = None

        class UseCaseStub:
            async def __call__(self, query):
                nonlocal recorded_query
                recorded_query = query
                return [
                    ProductDTO(
                        id=uuid4(),
                        created_at=now,
                        updated_at=now,
                        sku="SKU-1",
                        product_name="Running Shoe",
                        description=None,
                        category_id=category_id,
                    )
                ]

        context = _context()

        response = await list_products(
            context=context,
            use_case=UseCaseStub(),
            limit=10,
            offset=5,
            category_id=category_id,
        )

        self.assertEqual(
            recorded_query.tenant_id,
            EntityIdVO.from_value(context.principal.tenant_id),
        )
        self.assertEqual(recorded_query.category_id.uuid, category_id)
        self.assertEqual(response.limit, 10)
        self.assertEqual(response.offset, 5)
        self.assertEqual(response.count, 1)
