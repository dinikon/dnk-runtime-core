from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from src.modules.schema_registry.application.metadata.schema_registry_metadata_snapshot import (
    SchemaRegistryMetadataSnapshot,
)
from src.modules.schema_registry.application.migration.operations import (
    DropColumnOperation,
    DropForeignKeyOperation,
    DropIndexOperation,
    DropTableOperation,
)
from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    PhysicalSchemaSnapshot,
    TableSnapshot,
)
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.postgres_schema_plan_service import (
    PostgresSchemaPlanService,
)
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.application.use_case.diff_schema_use_case import (
    DiffSchemaUseCase,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedSchemaSpec,
)


def _column(name: str) -> ColumnSnapshot:
    return ColumnSnapshot(
        name=name,
        sql_preset=SqlTypePresetEnum.UUID,
        is_nullable=False,
        default_value=None,
    )


def _object(name: str, *, kind: ObjectKind, field_names: tuple[str, ...]):
    object_id = RuntimeObjectIdVO.from_value(uuid4())
    fields = [
        SimpleNamespace(
            id=RuntimeFieldIdVO.from_value(uuid4()),
            field_name=SimpleNamespace(value=field_name),
            kind=FieldKind.SYSTEM if field_name == "id" else FieldKind.CUSTOM,
        )
        for field_name in field_names
    ]
    return SimpleNamespace(
        id=object_id,
        kind=kind,
        object_name=SimpleNamespace(singular=name, plural=f"{name}s"),
        fields=fields,
    )


class RetiredSchemaArtifactTests(unittest.TestCase):
    def test_removes_relations_to_retired_objects_and_preserves_unrelated_custom_relations(
        self,
    ) -> None:
        contact = _object(
            "contact",
            kind=ObjectKind.STANDARD,
            field_names=("id",),
        )
        deal = _object(
            "c_deal",
            kind=ObjectKind.CUSTOM,
            field_names=("id", "contact_id"),
        )
        account = _object(
            "c_account",
            kind=ObjectKind.CUSTOM,
            field_names=("id",),
        )
        deal_contact = SimpleNamespace(
            id=RuntimeRelationIdVO.from_value(uuid4()),
            kind="custom",
            relation_type=RelationTypeEnum.MANY_TO_ONE,
            source_object_id=deal.id,
            target_object_id=contact.id,
            owning_object_id=deal.id,
            fk_field_id=deal.fields[1].id,
            referenced_object_id=contact.id,
            referenced_field_id=contact.fields[0].id,
            relation_table_name=None,
            source_join_column_name=None,
            target_join_column_name=None,
            is_unique=False,
        )
        deals_contacts = SimpleNamespace(
            id=RuntimeRelationIdVO.from_value(uuid4()),
            kind="custom",
            relation_type=RelationTypeEnum.MANY_TO_MANY,
            source_object_id=deal.id,
            target_object_id=contact.id,
            owning_object_id=None,
            fk_field_id=None,
            referenced_object_id=None,
            referenced_field_id=None,
            relation_table_name="c_deals_contacts",
            source_join_column_name="c_deal_id",
            target_join_column_name="contact_id",
            is_unique=False,
        )
        deals_accounts = SimpleNamespace(
            id=RuntimeRelationIdVO.from_value(uuid4()),
            kind="custom",
            relation_type=RelationTypeEnum.MANY_TO_MANY,
            source_object_id=deal.id,
            target_object_id=account.id,
            owning_object_id=None,
            fk_field_id=None,
            referenced_object_id=None,
            referenced_field_id=None,
            relation_table_name="deals_accounts",
            source_join_column_name="c_deal_id",
            target_join_column_name="c_account_id",
            is_unique=False,
        )
        snapshot = SchemaRegistryMetadataSnapshot(
            datasource=SimpleNamespace(),  # type: ignore[arg-type]
            objects=(contact, deal, account),  # type: ignore[arg-type]
            relations=(deal_contact, deals_contacts, deals_accounts),  # type: ignore[arg-type]
        )
        schema_spec = ValidatedSchemaSpec(
            version=None,
            code="crm",
            label="CRM",
            objects=(),
        )

        artifacts = DiffSchemaUseCase._build_preserved_artifacts(
            snapshot,
            schema_spec=schema_spec,
        )

        self.assertTrue(artifacts.removes_column("c_deals", "contact_id"))
        self.assertTrue(
            artifacts.removes_foreign_key(
                "c_deals",
                "fk_c_deals_contact_id_contacts",
            )
        )
        self.assertTrue(artifacts.removes_table("c_deals_contacts"))
        self.assertTrue(artifacts.has_table("deals_accounts"))

        plan_service = PostgresSchemaPlanService(
            field_type_catalog=FieldTypeCatalog(),
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
        )
        actual_schema = PhysicalSchemaSnapshot(
            schema_name="dnk_test",
            tables=(
                TableSnapshot(
                    name="contacts",
                    columns=(_column("id"),),
                ),
                TableSnapshot(
                    name="c_deals",
                    columns=(_column("id"), _column("contact_id")),
                    indexes=(
                        IndexSnapshot(
                            name="idx_c_deals_contact_id",
                            columns=("contact_id",),
                            is_unique=False,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="fk_c_deals_contact_id_contacts",
                            source_columns=("contact_id",),
                            target_table_name="contacts",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
                TableSnapshot(
                    name="c_deals_contacts",
                    columns=(
                        _column("id"),
                        _column("c_deal_id"),
                        _column("contact_id"),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="idx_c_deals_contacts_c_deal_id",
                            columns=("c_deal_id",),
                            is_unique=False,
                        ),
                        IndexSnapshot(
                            name="idx_c_deals_contacts_contact_id",
                            columns=("contact_id",),
                            is_unique=False,
                        ),
                        IndexSnapshot(
                            name="uq_c_deals_contacts_c_deal_id_contact_id",
                            columns=("c_deal_id", "contact_id"),
                            is_unique=True,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="fk_c_deals_contacts_c_deal_id_c_deals",
                            source_columns=("c_deal_id",),
                            target_table_name="c_deals",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                        ForeignKeySnapshot(
                            name="fk_c_deals_contacts_contact_id_contacts",
                            source_columns=("contact_id",),
                            target_table_name="contacts",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
                TableSnapshot(
                    name="deals_accounts",
                    columns=(
                        _column("id"),
                        _column("c_deal_id"),
                        _column("c_account_id"),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name="idx_deals_accounts_c_deal_id",
                            columns=("c_deal_id",),
                            is_unique=False,
                        ),
                        IndexSnapshot(
                            name="idx_deals_accounts_c_account_id",
                            columns=("c_account_id",),
                            is_unique=False,
                        ),
                        IndexSnapshot(
                            name="uq_deals_accounts_c_deal_id_c_account_id",
                            columns=("c_deal_id", "c_account_id"),
                            is_unique=True,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name="fk_deals_accounts_c_deal_id_c_deals",
                            source_columns=("c_deal_id",),
                            target_table_name="c_deals",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                        ForeignKeySnapshot(
                            name="fk_deals_accounts_c_account_id_c_accounts",
                            source_columns=("c_account_id",),
                            target_table_name="c_accounts",
                            target_columns=("id",),
                            on_delete="restrict",
                        ),
                    ),
                ),
            ),
        )

        plan = plan_service.build_diff_plan(
            schema_name="dnk_test",
            seed=schema_spec,
            actual_schema=actual_schema,
            preserved_artifacts=artifacts,
        )

        self.assertTrue(
            any(
                isinstance(operation, DropForeignKeyOperation)
                and operation.constraint_name == "fk_c_deals_contact_id_contacts"
                for operation in plan.destructive_operations
            )
        )
        self.assertTrue(
            any(
                isinstance(operation, DropIndexOperation)
                and operation.index_name == "idx_c_deals_contact_id"
                for operation in plan.destructive_operations
            )
        )
        self.assertTrue(
            any(
                isinstance(operation, DropColumnOperation)
                and operation.table_name == "c_deals"
                and operation.column_name == "contact_id"
                for operation in plan.destructive_operations
            )
        )
        dropped_tables = {
            operation.table_name
            for operation in plan.destructive_operations
            if isinstance(operation, DropTableOperation)
        }
        self.assertIn("contacts", dropped_tables)
        self.assertIn("c_deals_contacts", dropped_tables)
        self.assertNotIn("c_deals", dropped_tables)
        self.assertNotIn("deals_accounts", dropped_tables)


if __name__ == "__main__":
    unittest.main()
