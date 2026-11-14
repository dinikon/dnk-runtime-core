from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
    SupplierModelKey,
)

"""Сценарии справочника источников и правила HTTP PATCH."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from pydantic import ValidationError
from src.modules.supplier_sourcing.application.supplier_source.command.create_supplier_source.command import (
    CreateSupplierSourceCommand,
)
from src.modules.supplier_sourcing.application.supplier_source.command.create_supplier_source.handler import (
    CreateSupplierSourceHandler,
)
from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.command import (
    UpdateSupplierSourceCommand,
)
from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.handler import (
    UpdateSupplierSourceHandler,
)
from src.modules.supplier_sourcing.application.supplier_source.stock_update_policy import (
    SupplierStockUpdatePolicyInput,
)
from src.modules.supplier_sourcing.application.supplier_source.port.supplier_reference import (
    SupplierReference,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierNotFoundError,
    SupplierSourceNotFoundError,
    InvalidSupplierSourceValueError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode as Mode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior as Stale,
    MissingSkuBehavior as Missing,
)
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO
from src.modules.supplier_sourcing.presentation.supplier_source.http.request.patch_supplier_source import (
    PatchSupplierSourceRequest,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.request.put_supplier_source import (
    PutSupplierSourceRequest,
)
from src.modules.crm.application.company.command.delete_company.command import (
    DeleteCompanyCommand,
)
from src.modules.crm.application.company.command.delete_company.handler import (
    DeleteCompanyHandler,
)
from src.modules.crm.domain.company.error import CompanyInUseError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SupplierSourceApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.id, self.supplier_id = uuid4(), uuid4()
        self.repository = Mock(
            add=AsyncMock(), save=AsyncMock(), get_for_update=AsyncMock()
        )
        self.suppliers = Mock(
            get=AsyncMock(
                return_value=SupplierReference(
                    SupplierReferenceVO.from_value("crm.company", self.supplier_id),
                    "Company",
                )
            )
        )
        self.command = CreateSupplierSourceCommand(
            SupplierReferenceVO.from_value("crm.company", self.supplier_id),
            "  Source A ",
            frozenset((Mode.DROPSHIP,)),
            0,
            SupplierStockUpdatePolicyInput(
                3600, Stale.MARK_UNKNOWN, Missing.MARK_UNKNOWN
            ),
            " 000Code-a ",
        )
        self.create = CreateSupplierSourceHandler(
            self.repository, self.suppliers, Mock(new=Mock(return_value=self.id))
        )
        self.result = await self.create.execute(self.command)
        self.source = self.repository.add.await_args.args[0]
        self.repository.get_for_update.return_value = self.source
        self.update = UpdateSupplierSourceHandler(self.repository, self.suppliers)

    async def test_create_uses_factory_and_protects_supplier(self) -> None:
        self.assertEqual(
            (
                self.result.name,
                self.result.external_warehouse_code,
                self.result.is_active,
            ),
            ("Source A", "000Code-a", True),
        )
        self.assertEqual(self.result.supplier_name, "Company")
        self.suppliers.get.assert_awaited_once_with(
            SupplierReferenceVO.from_value("crm.company", self.supplier_id), lock=True
        )
        self.suppliers.get.return_value = None
        with self.assertRaises(SupplierNotFoundError):
            await self.create.execute(self.command)
        self.repository.add.assert_awaited_once()

    async def test_patch_merges_fulfillment_and_preserves_false_zero_null(self) -> None:
        result = await self.update.execute(
            UpdateSupplierSourceCommand(
                self.source.id,
                frozenset(
                    (
                        "default_lead_time_seconds",
                        "is_active",
                        "external_warehouse_code",
                    )
                ),
                default_lead_time_seconds=0,
                is_active=False,
                external_warehouse_code=None,
            )
        )
        self.assertEqual(
            (
                result.fulfillment_modes,
                result.default_lead_time_seconds,
                result.is_active,
                result.external_warehouse_code,
            ),
            ((Mode.DROPSHIP,), 0, False, None),
        )
        updated = self.repository.save.await_args.args[0]
        self.assertEqual(
            (updated.id, updated.supplier), (self.source.id, self.source.supplier)
        )
        self.assertEqual(updated.stock_update_policy, self.source.stock_update_policy)
        await self.update.execute(
            UpdateSupplierSourceCommand(
                self.source.id,
                frozenset(("fulfillment_modes",)),
                fulfillment_modes=frozenset((Mode.PURCHASE_TO_WAREHOUSE,)),
            )
        )
        self.assertEqual(
            self.repository.save.await_args.args[0].default_lead_time.value,
            timedelta(0),
        )

    async def test_domain_rejects_empty_modes_before_write(self) -> None:
        with self.assertRaises(InvalidSupplierSourceValueError):
            await self.update.execute(
                UpdateSupplierSourceCommand(
                    self.source.id,
                    frozenset(("fulfillment_modes",)),
                    fulfillment_modes=frozenset(),
                )
            )
        self.repository.save.assert_not_awaited()

    async def test_missing_source_and_noop(self) -> None:
        await self.update.execute(
            UpdateSupplierSourceCommand(
                self.source.id, frozenset(("name",)), name="Source A"
            )
        )
        self.repository.save.assert_not_awaited()
        self.repository.get_for_update.return_value = None
        with self.assertRaises(SupplierSourceNotFoundError):
            await self.update.execute(
                UpdateSupplierSourceCommand(
                    self.source.id, frozenset(("name",)), name="Other"
                )
            )

    async def test_policy_replaced_atomically(self) -> None:
        policy = SupplierStockUpdatePolicyInput(
            900, Stale.BLOCK_AUTOMATIC_SALE, Missing.KEEP_LAST
        )
        result = await self.update.execute(
            UpdateSupplierSourceCommand(
                self.source.id,
                frozenset(("stock_update_policy",)),
                stock_update_policy=policy,
            )
        )
        self.assertEqual(
            (
                result.stock_ttl_seconds,
                result.stale_behavior,
                result.missing_sku_behavior,
            ),
            (900, Stale.BLOCK_AUTOMATIC_SALE, Missing.KEEP_LAST),
        )

    async def test_company_usage_rejects_delete_before_contact_side_effects(
        self,
    ) -> None:
        from src.modules.crm.domain.company.aggregate import CompanyEntity
        from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO

        company = CompanyEntity.create(
            company_id=CompanyIdVO(self.supplier_id),
            legal_name="Supplier",
            actor_id=EntityIdVO(uuid4()),
            now=datetime(2026, 11, 14, tzinfo=UTC),
        )
        repository = Mock(
            get_for_update=AsyncMock(return_value=company), delete=AsyncMock()
        )
        points = Mock(remove=AsyncMock())
        handler = DeleteCompanyHandler(
            repository, points, Mock(is_used=AsyncMock(return_value=True))
        )
        with self.assertRaises(CompanyInUseError):
            await handler.execute(DeleteCompanyCommand(company.id, EntityIdVO(uuid4())))
        points.remove.assert_not_awaited()
        repository.delete.assert_not_awaited()


class SupplierSourceRequestTests(unittest.TestCase):
    def test_rejects_unknown_empty_null_and_partial_policy(self) -> None:
        for payload in (
            {},
            {"supplier_id": str(uuid4())},
            {"name": None},
            {"is_active": None},
            {"fulfillment_modes": None},
            {"stock_update_policy": {"ttl_seconds": 1}},
            {"default_lead_time_seconds": True},
            {"default_lead_time_seconds": 1.5},
            {"stock_update_policy": None},
            {"fulfillment_modes": ["DROPSHIP", "DROPSHIP"]},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                PatchSupplierSourceRequest.model_validate(payload)

    def test_accepts_null_false_zero_and_requires_all_put_fields(self) -> None:
        value = PatchSupplierSourceRequest.model_validate(
            {
                "external_warehouse_code": None,
                "default_lead_time_seconds": 0,
                "is_active": False,
            }
        )
        self.assertEqual(
            value.model_fields_set,
            {"external_warehouse_code", "default_lead_time_seconds", "is_active"},
        )
        with self.assertRaises(ValidationError):
            PutSupplierSourceRequest.model_validate({"name": "Only name"})


class SupplierSourceArchitectureTests(unittest.TestCase):
    def test_public_routes_and_tenant_registration(self) -> None:
        """Справочник и селектор CRM зарегистрированы; tenant-модели принадлежат Tenancy."""
        from src.app_factory import create_app
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
            migration_metadata,
        )

        schema = create_app().openapi()
        self.assertEqual(
            set(schema["paths"]["/api/console/supplier-sourcing/sources"]),
            {"get", "post"},
        )
        self.assertEqual(
            set(schema["paths"]["/api/console/supplier-sourcing/sources/{source_id}"]),
            {"get", "put", "patch"},
        )
        self.assertIn("/api/console/crm/counterparty-references", schema["paths"])
        tables = migration_metadata().tables
        self.assertTrue(
            {"supplier_sources", "supplier_source_fulfillment_modes"} <= set(tables)
        )
        self.assertFalse(tables["supplier_sources"].foreign_key_constraints)
        self.assertIn(
            ("supplier_model_key", "supplier_id"),
            {
                tuple(column.name for column in index.columns)
                for index in tables["supplier_sources"].indexes
            },
        )

    def test_application_has_no_infrastructure_and_packages_are_empty(self) -> None:
        """Application не зависит от ORM/HTTP, SQL остаётся во внешнем слое."""
        import ast
        from pathlib import Path

        folder = Path(__file__).resolve().parents[1] / "src/modules/supplier_sourcing"
        for path in folder.rglob("*.py"):
            tree = ast.parse(path.read_text())
            if path.name == "__init__.py":
                self.assertFalse(tree.body, str(path))
            if "application" in path.parts or "domain" in path.parts:
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        self.assertFalse(
                            any(
                                token in (node.module or "").split(".")
                                for token in (
                                    "infrastructure",
                                    "presentation",
                                    "sqlalchemy",
                                    "pydantic",
                                    "fastapi",
                                )
                            ),
                            str(path),
                        )
