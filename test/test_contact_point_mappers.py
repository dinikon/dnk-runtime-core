"""Explicit persistence mappings and presentation ordering, without a database."""

from datetime import UTC, datetime, timedelta, tzinfo
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from uuid import uuid4

from src.modules.contact_points.infrastructure.persistence.mappers import (
    ContactPointMapper,
    ContactPointBindingMapper,
    ContactPointLabelMapper,
)
from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointPersistenceMappingError,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.binding.value_object.identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
    ContactPointValueVO,
)
from src.modules.contact_points.domain.label.value_object.name import (
    ContactPointLabelNameVO,
)
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.application.label.use_case.list_labels import (
    ListContactPointLabelsUseCase,
)
from src.modules.contact_points.application.label.query.list_labels_query import (
    ListContactPointLabelsQuery,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class NoOffsetTimezone(tzinfo):
    def utcoffset(self, dt):
        return None


class ContactPointMapperTests(TestCase):
    def setUp(self):
        now = datetime(2026, 9, 25, 12, tzinfo=UTC)
        self.point = dict(
            id=uuid4(),
            type="phone",
            canonical_value="+380501234567",
            country_code="UA",
            created_at=now,
            updated_at=now + timedelta(days=1),
            created_by=uuid4(),
            updated_by=uuid4(),
        )
        self.binding = dict(
            id=uuid4(),
            contact_point_id=self.point["id"],
            model_key="crm.contact",
            record_id=uuid4(),
            label_id=uuid4(),
            position=3,
            created_at=now + timedelta(hours=1),
            updated_at=now + timedelta(days=2),
            created_by=uuid4(),
            updated_by=uuid4(),
        )
        self.label = dict(
            id=self.binding["label_id"],
            type="phone",
            name="Рабочий",
            is_active=False,
            created_at=now + timedelta(hours=2),
            updated_at=now + timedelta(days=3),
            created_by=uuid4(),
            updated_by=uuid4(),
        )

    def assert_audit(self, entity, row):
        self.assertEqual(entity.created_at, row["created_at"])
        self.assertEqual(entity.updated_at, row["updated_at"])
        self.assertEqual(
            entity.created_by,
            EntityIdVO(row["created_by"]) if row["created_by"] is not None else None,
        )
        self.assertEqual(
            entity.updated_by,
            EntityIdVO(row["updated_by"]) if row["updated_by"] is not None else None,
        )

    def test_point_fields_and_insert_values(self):
        entity = ContactPointMapper.to_domain(self.point)
        self.assertEqual(entity.id, ContactPointIdVO(self.point["id"]))
        self.assertEqual(entity.type, ContactPointType.PHONE)
        self.assertEqual(entity.canonical_value, ContactPointValueVO("+380501234567"))
        self.assertEqual(entity.country_code, "UA")
        self.assert_audit(entity, self.point)
        self.assertEqual(ContactPointMapper.to_insert_values(entity), self.point)
        email = dict(
            self.point,
            type="email",
            canonical_value="User@example.com",
            country_code=None,
        )
        entity = ContactPointMapper.to_domain(email)
        self.assertEqual(entity.type, ContactPointType.EMAIL)
        self.assertIsNone(entity.country_code)
        self.assertEqual(entity.canonical_value.value, "User@example.com")
        self.assertEqual(ContactPointMapper.to_insert_values(entity), email)

    def test_binding_fields_nullable_label_and_target_projection(self):
        entity = ContactPointBindingMapper.to_domain(self.binding)
        self.assertEqual(entity.id, ContactPointBindingIdVO(self.binding["id"]))
        self.assertEqual(entity.contact_point_id, ContactPointIdVO(self.point["id"]))
        target = ContactPointTargetVO(
            "crm.contact", EntityIdVO(self.binding["record_id"])
        )
        self.assertEqual(entity.target, target)
        self.assertEqual(entity.label_id, ContactPointLabelIdVO(self.label["id"]))
        self.assertEqual(entity.position, 3)
        self.assert_audit(entity, self.binding)
        self.assertEqual(
            ContactPointBindingMapper.to_insert_values(entity), self.binding
        )
        self.assertEqual(
            ContactPointBindingMapper.to_target(
                {"model_key": "crm.contact", "record_id": self.binding["record_id"]}
            ),
            target,
        )
        row = dict(self.binding, label_id=None)
        entity = ContactPointBindingMapper.to_domain(row)
        self.assertIsNone(entity.label_id)
        self.assertEqual(ContactPointBindingMapper.to_insert_values(entity), row)

    def test_label_fields_and_mutable_update_fields_only(self):
        entity = ContactPointLabelMapper.to_domain(self.label)
        self.assertEqual(entity.id, ContactPointLabelIdVO(self.label["id"]))
        self.assertEqual(entity.type, ContactPointType.PHONE)
        self.assertEqual(entity.name, ContactPointLabelNameVO("Рабочий"))
        self.assertIs(entity.is_active, False)
        self.assert_audit(entity, self.label)
        self.assertEqual(ContactPointLabelMapper.to_insert_values(entity), self.label)
        entity.update(
            name="Новый",
            is_active=True,
            actor_id=EntityIdVO(uuid4()),
            now=self.label["updated_at"] + timedelta(days=1),
        )
        self.assertEqual(
            ContactPointLabelMapper.to_update_values(entity),
            {
                "name": "Новый",
                "is_active": True,
                "updated_at": entity.updated_at,
                "updated_by": entity.updated_by.uuid,
            },
        )
        for actors in (
            {"created_by": None, "updated_by": None},
            {"created_by": None, "updated_by": self.label["updated_by"]},
        ):
            row = dict(self.label, **actors)
            entity = ContactPointLabelMapper.to_domain(row)
            self.assert_audit(entity, row)
            self.assertEqual(ContactPointLabelMapper.to_insert_values(entity), row)
            self.assertEqual(
                ContactPointLabelMapper.to_update_values(entity)["updated_by"],
                row["updated_by"],
            )

    def test_join_keeps_point_and_binding_ids_and_audit_separate(self):
        row = dict(
            self.binding,
            point_id=self.point["id"],
            point_type=self.point["type"],
            point_canonical_value=self.point["canonical_value"],
            point_country_code=self.point["country_code"],
            point_created_at=self.point["created_at"],
            point_updated_at=self.point["updated_at"],
            point_created_by=self.point["created_by"],
            point_updated_by=self.point["updated_by"],
        )
        projection = ContactPointBindingMapper.to_bound_domain(row)
        self.assertEqual(
            projection.binding, ContactPointBindingMapper.to_domain(self.binding)
        )
        self.assertEqual(projection.point, ContactPointMapper.to_domain(self.point))
        self.assertNotEqual(projection.binding.id.uuid, projection.point.id.uuid)
        self.assertNotEqual(projection.binding.created_at, projection.point.created_at)
        del row["point_created_by"]
        with self.assertRaises(ContactPointPersistenceMappingError) as caught:
            ContactPointBindingMapper.to_bound_domain(row)
        self.assertIsInstance(caught.exception.__cause__, KeyError)

    def test_uuid_strings_are_supported_and_insert_values_have_no_tenant(self):
        for mapper, row, fields in (
            (ContactPointMapper, self.point, ("id", "created_by", "updated_by")),
            (
                ContactPointBindingMapper,
                self.binding,
                (
                    "id",
                    "contact_point_id",
                    "record_id",
                    "label_id",
                    "created_by",
                    "updated_by",
                ),
            ),
            (ContactPointLabelMapper, self.label, ("id", "created_by", "updated_by")),
        ):
            with self.subTest(mapper=mapper.__name__):
                strings = dict(row)
                for field in fields:
                    strings[field] = str(row[field])
                values = mapper.to_insert_values(mapper.to_domain(strings))
                self.assertEqual(values, row)
                self.assertNotIn("tenant_id", values)

    def test_corrupt_persisted_fields_raise_mapping_error_with_cause(self):
        cases = (
            (ContactPointMapper, self.point, {"type": "fax"}),
            (ContactPointMapper, self.point, {"canonical_value": ""}),
            (ContactPointMapper, self.point, {"canonical_value": 123}),
            (ContactPointMapper, self.point, {"country_code": 1}),
            (ContactPointMapper, self.point, {"country_code": None}),
            (ContactPointMapper, self.point, {"created_by": None}),
            (ContactPointBindingMapper, self.binding, {"contact_point_id": "bad-uuid"}),
            (ContactPointBindingMapper, self.binding, {"record_id": False}),
            (ContactPointBindingMapper, self.binding, {"model_key": "Bad Key"}),
            (ContactPointBindingMapper, self.binding, {"position": True}),
            (ContactPointBindingMapper, self.binding, {"position": -1}),
            (ContactPointBindingMapper, self.binding, {"label_id": 5}),
            (ContactPointBindingMapper, self.binding, {"updated_by": None}),
            (ContactPointLabelMapper, self.label, {"is_active": 1}),
            (ContactPointLabelMapper, self.label, {"name": "   "}),
            (ContactPointLabelMapper, self.label, {"updated_by": False}),
        )
        for mapper, row, changes in cases:
            with self.subTest(mapper=mapper.__name__, changes=changes):
                with self.assertRaises(ContactPointPersistenceMappingError) as caught:
                    mapper.to_domain(dict(row, **changes))
                self.assertIsNotNone(caught.exception.__cause__)
        for mapper, row in (
            (ContactPointMapper, self.point),
            (ContactPointBindingMapper, self.binding),
            (ContactPointLabelMapper, self.label),
        ):
            for changes in (
                {"id": "invalid"},
                {"id": 123},
                {"created_at": datetime(2026, 1, 1)},
                {"updated_at": "2026-01-01"},
                {"updated_at": datetime(2026, 1, 1, tzinfo=NoOffsetTimezone())},
            ):
                with self.subTest(mapper=mapper.__name__, changes=changes):
                    with self.assertRaises(
                        ContactPointPersistenceMappingError
                    ) as caught:
                        mapper.to_domain(dict(row, **changes))
                    self.assertIsNotNone(caught.exception.__cause__)
            incomplete = dict(row)
            del incomplete["id"]
            with self.assertRaises(ContactPointPersistenceMappingError) as caught:
                mapper.to_domain(incomplete)
            self.assertIsInstance(caught.exception.__cause__, KeyError)


class LabelOrderingTests(IsolatedAsyncioTestCase):
    async def test_use_case_preserves_casefold_display_order_and_id_tiebreak(self):
        now = datetime.now(UTC)
        rows = [
            dict(
                id=uuid4(),
                type=kind,
                name=name,
                is_active=True,
                created_at=now,
                updated_at=now,
                created_by=None,
                updated_by=None,
            )
            for kind, name in [
                ("phone", "SS"),
                ("email", "z"),
                ("phone", "ß"),
                ("phone", "a"),
            ]
        ]
        labels = tuple(ContactPointLabelMapper.to_domain(row) for row in rows)
        repository = AsyncMock()
        repository.list.return_value = labels
        query = ListContactPointLabelsQuery(EntityIdVO(uuid4()))
        result = await ListContactPointLabelsUseCase(repository)(query)
        tied = sorted((labels[0].id, labels[2].id), key=str)
        self.assertEqual(
            [item.id for item in result], [labels[1].id, labels[3].id, *tied]
        )
        repository.list.assert_awaited_once_with(query.tenant_id, query.type)
