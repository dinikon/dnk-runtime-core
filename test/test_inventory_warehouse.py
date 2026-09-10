import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import ForeignKeyConstraint

from src.modules.inventory.domain.warehouse import (
    InvalidWarehouseTitleError,
    Warehouse,
    WarehouseIdVO,
    WarehouseSelfParentError,
)
from src.modules.inventory.infrastructure.persistence import WarehouseModel
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence import Base, TenantBase
from src.modules.shared.infrastructure.persistence.tenant_migration_metadata import (
    migration_metadata,
    managed_table_names,
)


class WarehouseTests(unittest.TestCase):
    def make(self, **changes):
        values = dict(
            warehouse_id=WarehouseIdVO.from_value(uuid4()),
            title=" Main ",
            actor_id=EntityIdVO.from_value(uuid4()),
            now=datetime.now(UTC),
        )
        values.update(changes)
        return Warehouse.create(**values)

    def test_root_and_child_and_audit(self):
        root = self.make()
        child = self.make(parent_id=root.id)
        self.assertEqual(root.title.value, "Main")
        self.assertIsNone(root.parent_id)
        self.assertEqual(child.parent_id, root.id)
        self.assertEqual(root.created_at, root.updated_at)
        self.assertEqual(root.created_by, root.updated_by)

    def test_invalid_titles(self):
        for title in ("", "  ", "x" * 256, None):
            with (
                self.subTest(title=title),
                self.assertRaises(InvalidWarehouseTitleError),
            ):
                self.make(title=title)
        self.assertEqual(len(self.make(title=" " + "x" * 255 + " ").title.value), 255)

    def test_identifiers_and_self_reference(self):
        warehouse_id = WarehouseIdVO.from_value(uuid4())
        with self.assertRaises(WarehouseSelfParentError):
            self.make(warehouse_id=warehouse_id, parent_id=warehouse_id)
        for changes in (
            {"warehouse_id": uuid4()},
            {"parent_id": EntityIdVO.from_value(uuid4())},
            {"actor_id": uuid4()},
        ):
            with self.subTest(changes=changes), self.assertRaises(EntityIdTypeError):
                self.make(**changes)

    def test_model_is_tenant_only_and_copy_rewrites_self_fk(self):
        self.assertNotIn("warehouses", Base.metadata.tables)
        self.assertIs(
            TenantBase.metadata.tables["tenant.warehouses"], WarehouseModel.__table__
        )
        copied = migration_metadata()
        table = copied.tables["warehouses"]
        self.assertIsNone(table.schema)
        fk = next(iter(table.foreign_keys))
        self.assertEqual(fk.target_fullname, "warehouses.id")
        self.assertIs(fk.column.table, table)
        self.assertEqual(WarehouseModel.__table__.schema, "tenant")
        self.assertNotIn("tenant_id", table.c)
        self.assertEqual(
            next(
                c for c in table.constraints if isinstance(c, ForeignKeyConstraint)
            ).ondelete,
            "RESTRICT",
        )
        self.assertIn("warehouses", managed_table_names(copied))
