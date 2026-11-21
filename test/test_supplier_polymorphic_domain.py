"""Составная идентичность поставщика во всех связанных доменных контекстах."""

from dataclasses import FrozenInstanceError, replace
import unittest
from uuid import uuid4
from test import test_supplier_offer_domain as offer_fixture
from test import test_supplier_availability_domain as availability_fixture
from test import test_inventory_fulfillment_supplier_domain as inventory_fixture
from test import test_supplier_fulfillment_order_domain as external_fixture
from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
    SupplierModelKey,
)
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)
from src.modules.supplier_sourcing.domain.supplier_offer.error import (
    SupplierOfferSourceMismatchError,
)
from src.modules.supplier_sourcing.domain.supplier_availability.error import (
    SupplierAvailabilityContextMismatchError,
)
from src.modules.external_fulfillment.domain.value_object.supplier_reference import (
    ExternalSupplierReferenceVO,
)
from src.modules.external_fulfillment.domain.error import (
    SupplierFulfillmentBasisMismatchError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_reference import (
    FulfillmentSupplierReferenceVO,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentPlanContextError,
)


class SupplierPolymorphicDomainTests(unittest.TestCase):
    def test_reference_is_immutable_and_model_is_part_of_identity(self) -> None:
        identifier = uuid4()
        company = SupplierReferenceVO.from_value("crm.company", identifier)
        contact = SupplierReferenceVO.from_value("crm.contact", identifier)
        self.assertNotEqual(company, contact)
        self.assertEqual(len({company, contact}), 2)
        with self.assertRaises(FrozenInstanceError):
            company.model_key = SupplierModelKey.CONTACT
        for kind in ("crm.deal", "", None):
            with (
                self.subTest(kind=kind),
                self.assertRaises(InvalidSupplierSourceValueError),
            ):
                SupplierReferenceVO.from_value(kind, identifier)
        with self.assertRaises(InvalidSupplierSourceValueError):
            SupplierReferenceVO("crm.company", SupplierIdVO(identifier))

    def test_each_context_has_its_own_typed_reference(self) -> None:
        identifier = uuid4()
        for factory in (
            SupplierReferenceVO,
            ExternalSupplierReferenceVO,
            FulfillmentSupplierReferenceVO,
        ):
            self.assertNotEqual(
                factory.from_value("crm.company", identifier),
                factory.from_value("crm.contact", identifier),
            )
        self.assertNotEqual(
            SupplierReferenceVO.from_value("crm.contact", identifier),
            ExternalSupplierReferenceVO.from_value("crm.contact", identifier),
        )

    def test_offer_cannot_use_source_of_other_type_with_same_uuid(self) -> None:
        f = offer_fixture.SupplierOfferDomainTests()
        f.setUp()
        contact = SupplierReferenceVO.from_value(
            "crm.contact", f.supplier.identifier.uuid
        )
        source = f.source(contact)
        with self.assertRaises(SupplierOfferSourceMismatchError):
            f.create(source=source.identity_snapshot())
        offer = f.create(supplier=contact, source=source.identity_snapshot())
        self.assertEqual(offer.supplier, source.supplier)
        self.assertEqual(
            source.identity_snapshot().supplier.model_key, SupplierModelKey.CONTACT
        )

    def test_availability_checks_full_identity(self) -> None:
        f = availability_fixture.SupplierAvailabilityDomainTests()
        f.setUp()
        foreign = replace(
            f.source,
            supplier=SupplierReferenceVO.from_value(
                "crm.contact", f.source.supplier.identifier.uuid
            ),
        )
        with self.assertRaises(SupplierAvailabilityContextMismatchError):
            f.create(source=foreign.availability_snapshot())

    def test_inventory_option_checks_full_supplier_identity(self) -> None:
        f = inventory_fixture.FulfillmentSupplierDomainTests()
        f.setUp()
        foreign = replace(
            f.option,
            offer_supplier=FulfillmentSupplierReferenceVO.from_value(
                "crm.contact", f.option.source_supplier.identifier.uuid
            ),
        )
        with self.assertRaises(FulfillmentPlanContextError):
            f.add(supplier_option=foreign)

    def test_external_order_rejects_mixed_types_but_supports_contact(self) -> None:
        f = external_fixture.SupplierFulfillmentOrderDomainTests()
        f.setUp()
        contact = ExternalSupplierReferenceVO.from_value(
            "crm.contact", f.source.supplier.identifier.uuid
        )
        with self.assertRaises(SupplierFulfillmentBasisMismatchError):
            f.create(source=replace(f.source, supplier=contact))
        order = f.create(
            source=replace(f.source, supplier=contact),
            offers=(replace(f.offer, supplier=contact),),
        )
        self.assertEqual(order.supplier, contact)
