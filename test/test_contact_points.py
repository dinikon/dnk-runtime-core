"""Contact point normalization, boundaries and immutable identity."""

import ast
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
import unittest
from uuid import uuid4

from src.modules.contact_points.domain.contact_point.entity import ContactPoint
from src.modules.contact_points.domain.contact_point.error import (
    InvalidContactPointError,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
    NormalizationContext,
)
from src.modules.contact_points.infrastructure.normalization.phone import (
    PhoneNormalizer,
)
from src.modules.contact_points.infrastructure.normalization.email import (
    EmailNormalizer,
)
from src.modules.crm.presentation.http.contact.requests.schemas import (
    UpdateContactRequest,
)
from src.modules.crm.presentation.http.contact_points import contact_point_inputs
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.uuid import UUID7Generator


class ContactPointsDomainTests(unittest.TestCase):
    def test_phone_country_and_e164(self):
        normalizer = PhoneNormalizer()
        for raw in ("050 123 45 67", "+38 (050) 123-45-67"):
            normalized = normalizer.normalize(raw, NormalizationContext("UA"))
            self.assertEqual(normalized.value.value, "+380501234567")
        # Shared +1 country prefix does not make a US number a Canadian number.
        self.assertEqual(
            normalizer.normalize(
                "+1 202 555 0123", NormalizationContext("US")
            ).country_code,
            "US",
        )
        for raw, country in [
            ("+12025550123", "CA"),
            ("123", "UA"),
            ("Call +380501234567", "UA"),
            ("+380501234567 or +380672222222", "UA"),
            ("0501234567", None),
            ("0501234567 ext 12", "UA"),
            ("+380501234567", "GB"),
        ]:
            with (
                self.subTest(raw=raw, country=country),
                self.assertRaises(InvalidContactPointError),
            ):
                normalizer.normalize(raw, NormalizationContext(country))

    def test_email_normalizes_domain_without_collapsing_local_part(self):
        normalizer = EmailNormalizer()
        normalize = lambda value: normalizer.normalize(
            value, NormalizationContext()
        ).value.value
        self.assertEqual(normalize(" Denis@Example.COM "), "Denis@example.com")
        self.assertNotEqual(
            normalize("denis+shop@gmail.com"), normalize("denis@gmail.com")
        )
        self.assertNotEqual(
            normalize("Denis@example.com"), normalize("denis@example.com")
        )
        for value in (
            "inikon.base.gmail.com",
            "foo@",
            "foo@localhost",
            "a b@example.com",
        ):
            with self.subTest(value=value), self.assertRaises(InvalidContactPointError):
                normalize(value)

    def test_canonical_point_is_immutable(self):
        point = ContactPoint.create(
            point_id=ContactPointIdVO.from_value(uuid4()),
            point_type=ContactPointType.EMAIL,
            normalized=EmailNormalizer().normalize(
                "x@example.com", NormalizationContext()
            ),
            actor_id=EntityIdVO.from_value(uuid4()),
            now=datetime.now(UTC),
        )
        with self.assertRaises(FrozenInstanceError):
            point.canonical_value = "other@example.com"

    def test_omitted_empty_and_null_request_lists(self):
        generator = UUID7Generator()
        omitted = contact_point_inputs(UpdateContactRequest(first_name="A"), generator)
        empty = contact_point_inputs(
            UpdateContactRequest(first_name="A", phones=[]), generator
        )
        self.assertIsNone(omitted["phones"])
        self.assertEqual(empty["phones"], ())
        self.assertIsNone(empty["emails"])
        with self.assertRaises(ValueError):
            UpdateContactRequest(first_name="A", phones=None)

    def test_binding_noop_rebind_and_position_invariants(self):
        from datetime import timedelta
        from src.modules.contact_points.domain.binding.entity import ContactPointBinding
        from src.modules.contact_points.domain.binding.value_object.identifier import (
            ContactPointBindingIdVO,
        )
        from src.modules.contact_points.domain.binding.value_object.target import (
            ContactPointTargetVO,
        )
        from src.modules.shared.domain.domain_error import DomainError

        actor = EntityIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        point_id = ContactPointIdVO.from_value(uuid4())
        binding = ContactPointBinding.create(
            binding_id=ContactPointBindingIdVO.from_value(uuid4()),
            point_id=point_id,
            target=ContactPointTargetVO("crm.contact", EntityIdVO.from_value(uuid4())),
            label_id=None,
            position=0,
            actor_id=actor,
            now=now,
        )
        self.assertFalse(
            binding.update(
                point_id=point_id,
                label_id=None,
                position=0,
                actor_id=actor,
                now=now + timedelta(seconds=1),
            )
        )
        self.assertEqual(binding.updated_at, now)
        original_id = binding.id
        replacement = ContactPointIdVO.from_value(uuid4())
        self.assertTrue(
            binding.update(
                point_id=replacement,
                label_id=None,
                position=1,
                actor_id=actor,
                now=now + timedelta(seconds=2),
            )
        )
        self.assertEqual(binding.id, original_id)
        self.assertEqual(binding.created_at, now)
        self.assertEqual(binding.contact_point_id, replacement)
        with self.assertRaises(DomainError):
            binding.update(
                point_id=replacement,
                label_id=None,
                position=-1,
                actor_id=actor,
                now=now,
            )
        self.assertEqual(binding.position, 1)

    def test_module_import_boundaries(self):
        root = Path(__file__).resolve().parents[1] / "src/modules"
        for path in (root / "contact_points").rglob("*.py"):
            imports = []
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            for name in imports:
                self.assertFalse(name.startswith("src.modules.crm"), str(path))
                if "/domain/" in str(path) or "/application/" in str(path):
                    self.assertFalse(
                        name.startswith(
                            (
                                "sqlalchemy",
                                "fastapi",
                                "pydantic",
                                "phonenumbers",
                                "email_validator",
                                "src.modules.contact_points.infrastructure",
                                "src.modules.contact_points.presentation",
                            )
                        ),
                        (str(path), name),
                    )
        for layer in ("domain", "application"):
            for path in (root / "crm" / layer).rglob("*.py"):
                self.assertNotIn("src.modules.contact_points", path.read_text())
        for path in (root / "shared").rglob("*.py"):
            self.assertNotIn("src.modules.contact_points", path.read_text())


if __name__ == "__main__":
    unittest.main()
