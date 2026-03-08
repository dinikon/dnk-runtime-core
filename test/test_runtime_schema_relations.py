import unittest
from uuid import UUID, uuid4

from src.modules.runtime_schema.application.relations.dto import (
    CreateRelationCommandDTO,
    DeleteRelationCommandDTO,
)
from src.modules.runtime_schema.application.relations.use_cases.create_relation import (
    CreateRelationUseCase,
)
from src.modules.runtime_schema.application.relations.use_cases.delete_relation import (
    DeleteRelationUseCase,
)
from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
)
from src.modules.runtime_schema.domain.errors import (
    FieldMetadataNotFoundError,
    FieldMetadataObjectMismatchError,
    ObjectMetadataNotFoundError,
    RelationJunctionTableAlreadyExistsError,
    RelationMetadataNotFoundError,
    RelationOwnerFieldRequiredError,
)
from src.modules.runtime_schema.domain.value_objects import (
    RuntimeSchemaFieldType,
)


class RuntimeSchemaRelationUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_many_to_one_relation_binds_owner_field(self) -> None:
        tenant_id = uuid4()
        deal = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_deals",
            name_singular="deal",
            name_plural="deals",
            label_singular="Deal",
            label_plural="Deals",
        )
        company = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_companies",
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
        )
        company_id = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=deal.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="company_id",
            label="Company",
            is_nullable=True,
        )
        company_pk = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=company.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="id",
            label="ID",
            is_nullable=False,
            is_unique=True,
        )
        objects = InMemoryObjectRepository((deal, company))
        fields = InMemoryFieldRepository((company_id, company_pk))
        relations = InMemoryRelationRepository()
        schema_manager = InMemoryRelationSchemaManager()
        use_case = CreateRelationUseCase(objects, fields, relations, schema_manager)

        result = await use_case.execute(
            CreateRelationCommandDTO(
                tenant_id=tenant_id,
                schema="dnk_schema_test",
                kind="many_to_one",
                source_object_metadata_id=deal.id,
                source_field_metadata_id=company_id.id,
                target_object_metadata_id=company.id,
                reverse_name_field="deals",
                reverse_label="Deals",
                on_delete="set_null",
            )
        )

        self.assertEqual(result.kind, "many_to_one")
        self.assertEqual(result.reverse_kind, "one_to_many")
        stored_relation = relations.get_by_source_field_sync(company_id.id)
        self.assertIsNotNone(stored_relation)
        assert stored_relation is not None
        self.assertEqual(stored_relation.target_object_metadata_id, company.id)
        self.assertEqual(company_id.relation_target_object_metadata_id, company.id)
        self.assertEqual(company_id.relation_target_field_metadata_id, company_pk.id)
        self.assertEqual(len(schema_manager.ensured_relations), 1)

    async def test_create_one_to_one_relation_marks_unique_owner_relation(self) -> None:
        tenant_id = uuid4()
        contact = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_contacts",
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
        )
        passport = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_passports",
            name_singular="passport",
            name_plural="passports",
            label_singular="Passport",
            label_plural="Passports",
        )
        passport_id = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=contact.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="passport_id",
            label="Passport",
            is_nullable=False,
            is_unique=True,
        )
        passport_pk = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=passport.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="id",
            label="ID",
            is_nullable=False,
            is_unique=True,
        )
        use_case = CreateRelationUseCase(
            InMemoryObjectRepository((contact, passport)),
            InMemoryFieldRepository((passport_id, passport_pk)),
            InMemoryRelationRepository(),
            InMemoryRelationSchemaManager(),
        )

        result = await use_case.execute(
            CreateRelationCommandDTO(
                tenant_id=tenant_id,
                schema="dnk_schema_test",
                kind="one_to_one",
                source_object_metadata_id=contact.id,
                source_field_metadata_id=passport_id.id,
                target_object_metadata_id=passport.id,
                is_required=True,
            )
        )

        self.assertEqual(result.kind, "one_to_one")
        self.assertEqual(result.reverse_kind, "one_to_one")

    async def test_create_many_to_many_relation_generates_junction_table(self) -> None:
        tenant_id = uuid4()
        deal = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_deals",
            name_singular="deal",
            name_plural="deals",
            label_singular="Deal",
            label_plural="Deals",
        )
        contact = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_contacts",
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
        )
        relations = InMemoryRelationRepository()
        schema_manager = InMemoryRelationSchemaManager()
        use_case = CreateRelationUseCase(
            InMemoryObjectRepository((deal, contact)),
            InMemoryFieldRepository(()),
            relations,
            schema_manager,
        )

        result = await use_case.execute(
            CreateRelationCommandDTO(
                tenant_id=tenant_id,
                schema="dnk_schema_test",
                kind="many_to_many",
                source_object_metadata_id=deal.id,
                source_field_metadata_id=None,
                target_object_metadata_id=contact.id,
            )
        )

        self.assertEqual(result.kind, "many_to_many")
        self.assertEqual(result.reverse_kind, "many_to_many")
        self.assertIsNotNone(result.junction_table_name)
        assert result.junction_table_name is not None
        self.assertTrue(result.junction_table_name.startswith("rel_deal_contact_"))
        self.assertEqual(len(relations.items), 1)
        self.assertEqual(
            schema_manager.ensured_relations[0].junction_table_name,
            result.junction_table_name,
        )

    async def test_delete_relation_unbinds_owner_field(self) -> None:
        tenant_id = uuid4()
        lead = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_leads",
            name_singular="lead",
            name_plural="leads",
            label_singular="Lead",
            label_plural="Leads",
        )
        contact = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_contacts",
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
        )
        contact_id = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=lead.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="contact_id",
            label="Contact",
            is_nullable=True,
        )
        contact_pk = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=contact.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="id",
            label="ID",
            is_nullable=False,
            is_unique=True,
        )
        contact_id.bind_relation(contact.id, contact_pk.id)
        relation = RelationMetadata.create_many_to_one(
            tenant_id=tenant_id,
            source_object_metadata_id=lead.id,
            source_field_metadata_id=contact_id.id,
            target_object_metadata_id=contact.id,
            target_field_metadata_id=contact_pk.id,
            reverse_name_field="leads",
            reverse_label="Leads",
            is_system=True,
        )
        objects = InMemoryObjectRepository((lead, contact))
        fields = InMemoryFieldRepository((contact_id, contact_pk))
        relations = InMemoryRelationRepository((relation,))
        schema_manager = InMemoryRelationSchemaManager()
        use_case = DeleteRelationUseCase(objects, fields, relations, schema_manager)

        result = await use_case.execute(
            DeleteRelationCommandDTO(
                relation_id=relation.id,
                schema="dnk_schema_test",
            )
        )

        self.assertTrue(result.ok)
        self.assertIsNone(contact_id.relation_target_object_metadata_id)
        self.assertIsNone(contact_id.relation_target_field_metadata_id)
        self.assertFalse(relations.items[relation.id].is_active)
        self.assertEqual(len(schema_manager.dropped_relations), 1)

    async def test_create_relation_requires_owner_source_field_id(self) -> None:
        tenant_id = uuid4()
        deal = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_deals",
            name_singular="deal",
            name_plural="deals",
            label_singular="Deal",
            label_plural="Deals",
        )
        company = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_companies",
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
        )
        company_pk = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=company.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="id",
            label="ID",
            is_nullable=False,
            is_unique=True,
        )
        use_case = CreateRelationUseCase(
            InMemoryObjectRepository((deal, company)),
            InMemoryFieldRepository((company_pk,)),
            InMemoryRelationRepository(),
            InMemoryRelationSchemaManager(),
        )

        with self.assertRaises(RelationOwnerFieldRequiredError):
            await use_case.execute(
                CreateRelationCommandDTO(
                    tenant_id=tenant_id,
                    schema="dnk_schema_test",
                    kind="many_to_one",
                    source_object_metadata_id=deal.id,
                    source_field_metadata_id=None,
                    target_object_metadata_id=company.id,
                )
            )

    async def test_create_relation_raises_when_object_is_missing(self) -> None:
        tenant_id = uuid4()
        company = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_companies",
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
        )
        use_case = CreateRelationUseCase(
            InMemoryObjectRepository((company,)),
            InMemoryFieldRepository(()),
            InMemoryRelationRepository(),
            InMemoryRelationSchemaManager(),
        )

        with self.assertRaises(ObjectMetadataNotFoundError):
            await use_case.execute(
                CreateRelationCommandDTO(
                    tenant_id=tenant_id,
                    schema="dnk_schema_test",
                    kind="many_to_many",
                    source_object_metadata_id=uuid4(),
                    source_field_metadata_id=None,
                    target_object_metadata_id=company.id,
                )
            )

    async def test_create_relation_raises_when_field_is_missing(self) -> None:
        tenant_id = uuid4()
        deal = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_deals",
            name_singular="deal",
            name_plural="deals",
            label_singular="Deal",
            label_plural="Deals",
        )
        company = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_companies",
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
        )
        use_case = CreateRelationUseCase(
            InMemoryObjectRepository((deal, company)),
            InMemoryFieldRepository(()),
            InMemoryRelationRepository(),
            InMemoryRelationSchemaManager(),
        )

        with self.assertRaises(FieldMetadataNotFoundError):
            await use_case.execute(
                CreateRelationCommandDTO(
                    tenant_id=tenant_id,
                    schema="dnk_schema_test",
                    kind="many_to_one",
                    source_object_metadata_id=deal.id,
                    source_field_metadata_id=uuid4(),
                    target_object_metadata_id=company.id,
                )
            )

    async def test_create_relation_rejects_field_object_mismatch(self) -> None:
        tenant_id = uuid4()
        deal = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_deals",
            name_singular="deal",
            name_plural="deals",
            label_singular="Deal",
            label_plural="Deals",
        )
        company = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_companies",
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
        )
        contact = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_contacts",
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
        )
        foreign_field = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=contact.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="company_id",
            label="Company",
            is_nullable=True,
        )
        company_pk = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=company.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="id",
            label="ID",
            is_nullable=False,
            is_unique=True,
        )
        use_case = CreateRelationUseCase(
            InMemoryObjectRepository((deal, company, contact)),
            InMemoryFieldRepository((foreign_field, company_pk)),
            InMemoryRelationRepository(),
            InMemoryRelationSchemaManager(),
        )

        with self.assertRaises(FieldMetadataObjectMismatchError):
            await use_case.execute(
                CreateRelationCommandDTO(
                    tenant_id=tenant_id,
                    schema="dnk_schema_test",
                    kind="many_to_one",
                    source_object_metadata_id=deal.id,
                    source_field_metadata_id=foreign_field.id,
                    target_object_metadata_id=company.id,
                )
            )

    async def test_create_many_to_many_rejects_duplicate_junction_table(self) -> None:
        tenant_id = uuid4()
        deal = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_deals",
            name_singular="deal",
            name_plural="deals",
            label_singular="Deal",
            label_plural="Deals",
        )
        contact = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_contacts",
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
        )
        existing_relation = RelationMetadata.create_many_to_many(
            tenant_id=tenant_id,
            source_object_metadata_id=deal.id,
            target_object_metadata_id=contact.id,
            junction_table_name="rel_deal_contact_fixed",
        )
        use_case = CreateRelationUseCase(
            InMemoryObjectRepository((deal, contact)),
            InMemoryFieldRepository(()),
            InMemoryRelationRepository((existing_relation,)),
            InMemoryRelationSchemaManager(),
        )

        with self.assertRaises(RelationJunctionTableAlreadyExistsError):
            await use_case.execute(
                CreateRelationCommandDTO(
                    tenant_id=tenant_id,
                    schema="dnk_schema_test",
                    kind="many_to_many",
                    source_object_metadata_id=deal.id,
                    source_field_metadata_id=None,
                    target_object_metadata_id=contact.id,
                    junction_table_name="rel_deal_contact_fixed",
                )
            )

    async def test_delete_relation_raises_when_relation_missing(self) -> None:
        use_case = DeleteRelationUseCase(
            InMemoryObjectRepository(()),
            InMemoryFieldRepository(()),
            InMemoryRelationRepository(),
            InMemoryRelationSchemaManager(),
        )

        with self.assertRaises(RelationMetadataNotFoundError):
            await use_case.execute(
                DeleteRelationCommandDTO(
                    relation_id=uuid4(),
                    schema="dnk_schema_test",
                )
            )

    async def test_delete_relation_raises_when_owner_field_missing(self) -> None:
        tenant_id = uuid4()
        lead = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_leads",
            name_singular="lead",
            name_plural="leads",
            label_singular="Lead",
            label_plural="Leads",
        )
        contact = ObjectMetadata.create_system(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            table_name="crm_contacts",
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
        )
        contact_pk = FieldMetadata.create_system(
            tenant_id=tenant_id,
            object_metadata_id=contact.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="id",
            label="ID",
            is_nullable=False,
            is_unique=True,
        )
        relation = RelationMetadata.create_many_to_one(
            tenant_id=tenant_id,
            source_object_metadata_id=lead.id,
            source_field_metadata_id=uuid4(),
            target_object_metadata_id=contact.id,
            target_field_metadata_id=contact_pk.id,
            is_system=True,
        )
        use_case = DeleteRelationUseCase(
            InMemoryObjectRepository((lead, contact)),
            InMemoryFieldRepository((contact_pk,)),
            InMemoryRelationRepository((relation,)),
            InMemoryRelationSchemaManager(),
        )

        with self.assertRaises(FieldMetadataNotFoundError):
            await use_case.execute(
                DeleteRelationCommandDTO(
                    relation_id=relation.id,
                    schema="dnk_schema_test",
                )
            )


class InMemoryObjectRepository:
    def __init__(self, items: tuple[ObjectMetadata, ...]) -> None:
        self.items = {item.id: item for item in items}

    async def get_by_id(self, object_metadata_id: UUID) -> ObjectMetadata | None:
        return self.items.get(object_metadata_id)

    async def get_by_tenant_and_name_singular(
        self,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None:
        for item in self.items.values():
            if item.tenant_id == tenant_id and item.name_singular == name_singular:
                return item
        return None


class InMemoryFieldRepository:
    def __init__(self, items: tuple[FieldMetadata, ...]) -> None:
        self.items = {item.id: item for item in items}

    async def get_by_id(self, field_metadata_id: UUID) -> FieldMetadata | None:
        return self.items.get(field_metadata_id)

    async def save(self, field_metadata: FieldMetadata) -> None:
        self.items[field_metadata.id] = field_metadata

    async def get_by_object_and_name_field(
        self,
        object_metadata_id: UUID,
        name_field: str,
    ) -> FieldMetadata | None:
        for item in self.items.values():
            if (
                item.object_metadata_id == object_metadata_id
                and item.name_field == name_field
            ):
                return item
        return None


class InMemoryRelationRepository:
    def __init__(self, items: tuple[RelationMetadata, ...] = ()) -> None:
        self.items = {item.id: item for item in items}

    async def add(self, relation_metadata: RelationMetadata) -> None:
        self.items[relation_metadata.id] = relation_metadata

    async def save(self, relation_metadata: RelationMetadata) -> None:
        self.items[relation_metadata.id] = relation_metadata

    async def get_by_id(self, relation_id: UUID) -> RelationMetadata | None:
        return self.items.get(relation_id)

    async def get_by_source_field_id(
        self,
        source_field_metadata_id: UUID,
    ) -> RelationMetadata | None:
        return self.get_by_source_field_sync(source_field_metadata_id)

    def get_by_source_field_sync(
        self,
        source_field_metadata_id: UUID,
    ) -> RelationMetadata | None:
        for item in self.items.values():
            if (
                item.source_field_metadata_id == source_field_metadata_id
                and item.is_active
            ):
                return item
        return None

    async def exists_by_junction_table_name(self, junction_table_name: str) -> bool:
        return any(
            item.junction_table_name == junction_table_name and item.is_active
            for item in self.items.values()
        )


class InMemoryRelationSchemaManager:
    def __init__(self) -> None:
        self.ensured_relations: list[RelationMetadata] = []
        self.dropped_relations: list[RelationMetadata] = []

    async def ensure_relation(self, **kwargs) -> None:
        self.ensured_relations.append(kwargs["relation"])

    async def drop_relation(self, **kwargs) -> None:
        self.dropped_relations.append(kwargs["relation"])
