from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.shared.domain.errors import EntityIdTypeError
from src.modules.shared import EntityIdVO, TenantIdVO


class EntityIdVOTests(unittest.TestCase):
    def test_from_value_accepts_uuid_string_entity_id_and_same_id(self) -> None:
        raw_id = uuid4()
        base_id = EntityIdVO.from_value(raw_id)

        self.assertEqual(EntityIdVO.from_value(raw_id), base_id)
        self.assertEqual(EntityIdVO.from_value(str(raw_id)), base_id)
        self.assertIs(EntityIdVO.from_value(base_id), base_id)
        self.assertEqual(base_id.uuid, raw_id)

    def test_concrete_ids_inherit_entity_id_behavior(self) -> None:
        raw_id = uuid4()
        base_id = EntityIdVO.from_value(raw_id)
        contact_id = ContactIdVO.from_value(base_id)
        tenant_id = TenantIdVO.from_value(base_id)

        self.assertEqual(contact_id.uuid, raw_id)
        self.assertEqual(ContactIdVO.from_value(raw_id), contact_id)
        self.assertEqual(ContactIdVO.from_value(str(raw_id)), contact_id)
        self.assertIs(ContactIdVO.from_value(contact_id), contact_id)
        self.assertEqual(tenant_id.uuid, raw_id)
        self.assertIs(TenantIdVO.from_value(tenant_id), tenant_id)

    def test_different_concrete_id_classes_are_not_equal_for_same_uuid(self) -> None:
        raw_id = uuid4()

        self.assertNotEqual(
            ContactIdVO.from_value(raw_id),
            ProductIdVO.from_value(raw_id),
        )
        self.assertNotEqual(
            TenantIdVO.from_value(raw_id),
            ProductIdVO.from_value(raw_id),
        )

    def test_concrete_ids_are_not_interchangeable_in_from_value(self) -> None:
        contact_id = ContactIdVO.from_value(uuid4())

        with self.assertRaises(EntityIdTypeError):
            ProductIdVO.from_value(contact_id)


__all__ = ["EntityIdVOTests"]
