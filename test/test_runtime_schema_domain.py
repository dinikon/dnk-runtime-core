import unittest
from uuid import uuid4

from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
)
from src.modules.runtime_schema.domain.errors import (
    InvalidRequiredRelationOnDeleteError,
    RelationJunctionTableRequiredError,
    RelationOwnerFieldRequiredError,
    RelationTargetFieldRequiredError,
)
from src.modules.runtime_schema.domain.value_objects import (
    RuntimeSchemaFieldType,
    RuntimeSchemaRelationKind,
    RuntimeSchemaRelationOnDelete,
)


class RuntimeSchemaDomainTests(unittest.TestCase):
    def test_object_metadata_create_system_normalizes_values(self) -> None:
        object_metadata = ObjectMetadata.create_system(
            tenant_id=uuid4(),
            data_source_id=uuid4(),
            table_name=" CRM_DEALS ",
            name_singular=" Deal ",
            name_plural=" Deals ",
            label_singular=" Deal ",
            label_plural=" Deals ",
            description=" Desc ",
            icon=" briefcase ",
            shortcut=" D ",
        )

        self.assertEqual(object_metadata.table_name, "crm_deals")
        self.assertEqual(object_metadata.name_singular, "deal")
        self.assertEqual(object_metadata.name_plural, "deals")
        self.assertEqual(object_metadata.label_singular, "Deal")
        self.assertEqual(object_metadata.label_plural, "Deals")
        self.assertEqual(object_metadata.description, "Desc")
        self.assertEqual(object_metadata.icon, "briefcase")
        self.assertEqual(object_metadata.shortcut, "D")
        self.assertTrue(object_metadata.is_system)
        self.assertFalse(object_metadata.is_custom)

    def test_field_metadata_bind_and_unbind_relation(self) -> None:
        target_object_id = uuid4()
        target_field_id = uuid4()
        field_metadata = FieldMetadata.create_system(
            tenant_id=uuid4(),
            object_metadata_id=uuid4(),
            field_type=RuntimeSchemaFieldType.UUID,
            name_field=" Company_Id ",
            label=" Company ",
        )

        self.assertEqual(field_metadata.name_field, "company_id")
        self.assertEqual(field_metadata.label, "Company")
        field_metadata.bind_relation(target_object_id, target_field_id)
        self.assertEqual(
            field_metadata.relation_target_object_metadata_id, target_object_id
        )
        self.assertEqual(
            field_metadata.relation_target_field_metadata_id, target_field_id
        )
        field_metadata.unbind_relation()
        self.assertIsNone(field_metadata.relation_target_object_metadata_id)
        self.assertIsNone(field_metadata.relation_target_field_metadata_id)

    def test_relation_metadata_requires_source_field_for_owner_relation(self) -> None:
        with self.assertRaises(RelationOwnerFieldRequiredError):
            RelationMetadata._create(
                tenant_id=uuid4(),
                source_object_metadata_id=uuid4(),
                source_field_metadata_id=None,
                target_object_metadata_id=uuid4(),
                target_field_metadata_id=uuid4(),
                kind=RuntimeSchemaRelationKind.MANY_TO_ONE,
                reverse_name_field=None,
                reverse_label=None,
                junction_table_name=None,
                on_delete=RuntimeSchemaRelationOnDelete.RESTRICT,
                is_required=False,
                is_system=True,
            )

    def test_relation_metadata_requires_target_field_for_owner_relation(self) -> None:
        with self.assertRaises(RelationTargetFieldRequiredError):
            RelationMetadata._create(
                tenant_id=uuid4(),
                source_object_metadata_id=uuid4(),
                source_field_metadata_id=uuid4(),
                target_object_metadata_id=uuid4(),
                target_field_metadata_id=None,
                kind=RuntimeSchemaRelationKind.ONE_TO_ONE,
                reverse_name_field=None,
                reverse_label=None,
                junction_table_name=None,
                on_delete=RuntimeSchemaRelationOnDelete.RESTRICT,
                is_required=False,
                is_system=True,
            )

    def test_relation_metadata_rejects_required_set_null(self) -> None:
        with self.assertRaises(InvalidRequiredRelationOnDeleteError):
            RelationMetadata.create_many_to_one(
                tenant_id=uuid4(),
                source_object_metadata_id=uuid4(),
                source_field_metadata_id=uuid4(),
                target_object_metadata_id=uuid4(),
                target_field_metadata_id=uuid4(),
                on_delete=RuntimeSchemaRelationOnDelete.SET_NULL,
                is_required=True,
            )

    def test_relation_metadata_requires_junction_table_name(self) -> None:
        with self.assertRaises(RelationJunctionTableRequiredError):
            RelationMetadata._create(
                tenant_id=uuid4(),
                source_object_metadata_id=uuid4(),
                source_field_metadata_id=None,
                target_object_metadata_id=uuid4(),
                target_field_metadata_id=None,
                kind=RuntimeSchemaRelationKind.MANY_TO_MANY,
                reverse_name_field=" Tags ",
                reverse_label=" Tags ",
                junction_table_name=" ",
                on_delete=RuntimeSchemaRelationOnDelete.CASCADE,
                is_required=False,
                is_system=False,
            )

    def test_relation_metadata_normalizes_and_deactivates(self) -> None:
        relation = RelationMetadata.create_many_to_many(
            tenant_id=uuid4(),
            source_object_metadata_id=uuid4(),
            target_object_metadata_id=uuid4(),
            junction_table_name=" REL_DEAL_CONTACT ",
            reverse_name_field=" Contacts ",
            reverse_label=" Contacts ",
        )

        self.assertEqual(relation.junction_table_name, "rel_deal_contact")
        self.assertEqual(relation.reverse_name_field, "contacts")
        self.assertEqual(relation.reverse_label, "Contacts")
        self.assertEqual(relation.reverse_kind, RuntimeSchemaRelationKind.MANY_TO_MANY)
        relation.deactivate()
        self.assertFalse(relation.is_active)
