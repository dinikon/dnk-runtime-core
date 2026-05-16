from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.crm.application.contact.dto.contact_fields_description_dto import (
    ContactFieldOptionDTO,
)
from src.modules.crm.infrastructure.contact_model_description_repository import (
    ContactModelDescriptionRepository,
)
from src.modules.schema_registry.application.dto.runtime_object_description import (
    RuntimeFieldDescriptionDTO,
    RuntimeObjectDescriptionDTO,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


class ContactModelDescriptionRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_schema_registry_description_to_crm_dto(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        object_id = uuid4()
        status_field_id = uuid4()
        first_name_field_id = uuid4()

        class DescribeRuntimeObjectUseCaseStub:
            async def __call__(self, *, tenant_id, object_name):
                self.tenant_id = tenant_id
                self.object_name = object_name
                return RuntimeObjectDescriptionDTO(
                    id=object_id,
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Tenant contact registry.",
                    kind="standard",
                    fields=(
                        RuntimeFieldDescriptionDTO(
                            id=status_field_id,
                            field_name="status",
                            label="Status",
                            description="Contact status.",
                            type="select",
                            is_nullable=False,
                            default_value="'lead'",
                            kind="system",
                            options={
                                "lead": "Lead",
                                "customer": "Customer",
                            },
                        ),
                        RuntimeFieldDescriptionDTO(
                            id=first_name_field_id,
                            field_name="first_name",
                            label="First Name",
                            description="Contact first name.",
                            type="text",
                            is_nullable=False,
                            default_value=None,
                            kind="standard",
                            options={},
                        ),
                    ),
                )

        use_case_stub = DescribeRuntimeObjectUseCaseStub()

        class RuntimeObjectResolverStub:
            async def resolve(self, tenant_id, object_name):
                self.tenant_id = tenant_id
                self.object_name = object_name
                return RuntimeObjectDescriptor(
                    schema_name="dnk_test",
                    object_name="contact",
                    table_name="contacts",
                    pk="id",
                    title_field="id",
                    fields=(
                        RuntimeFieldDescriptor(
                            name="status",
                            type_code="select",
                            is_nullable=False,
                            default_value="'lead'",
                            options={
                                "lead": "Lead",
                                "customer": "Customer",
                            },
                            settings={},
                            kind="system",
                        ),
                        RuntimeFieldDescriptor(
                            name="first_name",
                            type_code="text",
                            is_nullable=False,
                            default_value=None,
                            options={},
                            settings={},
                        ),
                    ),
                    relations=(),
                )

        resolver_stub = RuntimeObjectResolverStub()
        repository = ContactModelDescriptionRepository(
            use_case_stub,
            runtime_object_resolver=resolver_stub,
        )

        description = await repository.describe_fields(tenant_id=tenant_id)

        self.assertEqual(use_case_stub.tenant_id, tenant_id)
        self.assertEqual(use_case_stub.object_name, "contact")
        self.assertEqual(resolver_stub.tenant_id, tenant_id)
        self.assertEqual(resolver_stub.object_name, "contact")
        self.assertEqual(description.object_description.id, object_id)
        self.assertEqual(description.object_description.singular_label, "Contact")
        self.assertEqual(description.object_description.plural_label, "Contacts")
        self.assertEqual(description.object_description.kind, "standard")
        self.assertEqual(
            [field.field_name for field in description.fields],
            ["status", "first_name"],
        )
        self.assertEqual(description.fields[0].default_value, "'lead'")
        self.assertEqual(description.fields[0].kind, "system")
        self.assertEqual(description.fields[1].kind, "standard")
        self.assertEqual(
            description.fields[0].filter.operators,
            ("eq", "neq", "in", "is_null", "is_not_null"),
        )
        self.assertEqual(description.fields[0].filter.input, "select")
        self.assertTrue(description.fields[0].sort.enabled)
        self.assertEqual(description.fields[1].filter.input, "text")
        self.assertIn("contains", description.fields[1].filter.operators)
        self.assertEqual(
            description.fields[0].options,
            (
                ContactFieldOptionDTO(value="lead", label="Lead"),
                ContactFieldOptionDTO(
                    value="customer",
                    label="Customer",
                ),
            ),
        )
        self.assertEqual(description.fields[1].options, ())
