from __future__ import annotations

import hashlib
import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.contact_point.application import (
    AttachContactPointCommand,
    AttachContactPointUseCase,
    DetachContactPointCommand,
    DetachContactPointUseCase,
)
from src.modules.contact_point.domain import (
    ContactPointBindingEntity,
    ContactPointBindingIdVO,
    ContactPointEntity,
    ContactPointIdVO,
    ContactPointOwnerNotFoundError,
    ContactPointTypeVO,
    InvalidContactPointValueError,
    OwnerContactPointBinding,
)
from src.modules.contact_point.infrastructure import (
    ContactPointHashService,
    ContactPointNormalizeService,
)
from src.modules.schema_registry.domain.object_feature import (
    ObjectFeatureNotEnabledError,
)
from src.modules.shared import EntityIdVO


class _Clock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _OwnerResolver:
    def __init__(self, exists: bool = True) -> None:
        self.result = exists
        self.calls: list[OwnerContactPointBinding] = []

    async def exists(self, *, tenant_id, owner):
        self.calls.append(owner)
        return self.result


class _FeatureGate:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.calls: list[EntityIdVO] = []

    async def assert_contact_point_enabled(self, *, tenant_id, owner_object_id):
        self.calls.append(owner_object_id)
        if self.exc is not None:
            raise self.exc


class _Repository:
    def __init__(self) -> None:
        self.contact_points: dict[ContactPointIdVO, ContactPointEntity] = {}
        self.bindings: dict[ContactPointBindingIdVO, ContactPointBindingEntity] = {}
        self.contact_point_saves = 0
        self.binding_saves = 0
        self.unset_calls = []

    async def load_contact_point(self, *, tenant_id, contact_point_id):
        return self.contact_points.get(contact_point_id)

    async def load_binding(self, *, tenant_id, binding_id):
        return self.bindings.get(binding_id)

    async def get_by_type_and_hash(
        self,
        *,
        tenant_id,
        contact_point_type,
        hash_value,
    ):
        for contact_point in self.contact_points.values():
            if (
                contact_point.contact_point_type == contact_point_type
                and contact_point.hash_value == hash_value
            ):
                return contact_point
        return None

    async def save_contact_point(self, *, tenant_id, contact_point):
        self.contact_point_saves += 1
        self.contact_points[contact_point.id] = contact_point
        return contact_point

    async def find_by_owner_and_contact_point(
        self,
        *,
        tenant_id,
        owner,
        contact_point_id,
    ):
        for binding in self.bindings.values():
            if binding.owner == owner and binding.contact_point_id == contact_point_id:
                return binding
        return None

    async def find_first_active_by_owner_and_type(
        self,
        *,
        tenant_id,
        owner,
        contact_point_type,
    ):
        candidates = [
            binding
            for binding in self.bindings.values()
            if binding.owner == owner
            and binding.contact_point_type == contact_point_type
            and binding.is_active
        ]
        candidates.sort(key=lambda item: (item.created_at, str(item.id)))
        return candidates[0] if candidates else None

    async def unset_primary_for_owner_and_type(
        self,
        *,
        tenant_id,
        owner,
        contact_point_type,
        exclude_binding_id=None,
    ) -> None:
        self.unset_calls.append((owner, contact_point_type, exclude_binding_id))
        for binding in self.bindings.values():
            if (
                binding.owner == owner
                and binding.contact_point_type == contact_point_type
                and binding.is_active
                and binding.is_primary
                and binding.id != exclude_binding_id
            ):
                binding.is_primary = False

    async def has_active_bindings_for_contact_point(
        self, *, tenant_id, contact_point_id
    ):
        return any(
            binding.contact_point_id == contact_point_id and binding.is_active
            for binding in self.bindings.values()
        )

    async def save_binding(self, *, tenant_id, binding):
        self.binding_saves += 1
        self.bindings[binding.id] = binding
        return binding


def _ids():
    return (
        EntityIdVO.from_value(uuid4()),
        EntityIdVO.from_value(uuid4()),
        EntityIdVO.from_value(uuid4()),
    )


def _contact_point(
    *,
    contact_point_id: ContactPointIdVO,
    contact_point_type: ContactPointTypeVO = ContactPointTypeVO.EMAIL,
    value: str = "user@example.com",
    now: datetime | None = None,
) -> ContactPointEntity:
    now = now or datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
    return ContactPointEntity.create(
        id_=contact_point_id,
        now=now,
        contact_point_type=contact_point_type,
        raw_value=value,
        display_value=value,
        normalized_value=value,
        hash_value=hashlib.sha256(value.encode("utf-8")).hexdigest(),
    )


class ContactPointServicesTests(unittest.TestCase):
    def test_normalizes_email_phone_and_hashes_canonical_value(self) -> None:
        normalizer = ContactPointNormalizeService()

        email = normalizer.normalize(
            contact_point_type=ContactPointTypeVO.EMAIL,
            raw_value="  USER@Example.COM ",
        )
        phone = normalizer.normalize(
            contact_point_type=ContactPointTypeVO.PHONE,
            raw_value="(067) 111-22-33",
        )

        self.assertEqual(email, "user@example.com")
        self.assertEqual(phone, "+380671112233")
        self.assertEqual(
            ContactPointHashService().hash(email),
            hashlib.sha256(b"user@example.com").hexdigest(),
        )

    def test_rejects_invalid_email_and_phone(self) -> None:
        normalizer = ContactPointNormalizeService()

        with self.assertRaises(InvalidContactPointValueError):
            normalizer.normalize(
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="broken",
            )
        with self.assertRaises(InvalidContactPointValueError):
            normalizer.normalize(
                contact_point_type=ContactPointTypeVO.PHONE,
                raw_value="123",
            )


class ContactPointUseCaseTests(unittest.IsolatedAsyncioTestCase):
    def _attach_use_case(
        self,
        repository: _Repository,
        owner_resolver: _OwnerResolver | None = None,
        feature_gate: _FeatureGate | None = None,
        now: datetime | None = None,
    ) -> AttachContactPointUseCase:
        contact_point_id = ContactPointIdVO.from_value(uuid4())
        binding_id = ContactPointBindingIdVO.from_value(uuid4())
        return AttachContactPointUseCase(
            contact_points=repository,
            bindings=repository,
            owner_resolver=owner_resolver or _OwnerResolver(),
            feature_gate=feature_gate or _FeatureGate(),
            normalizer=ContactPointNormalizeService(),
            hash_service=ContactPointHashService(),
            contact_point_id_provider=lambda: contact_point_id,
            binding_id_provider=lambda: binding_id,
            clock=_Clock(now or datetime(2026, 5, 21, 10, 0, tzinfo=UTC)),
        )

    async def test_attach_creates_contact_point_and_binding(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        repository = _Repository()
        use_case = self._attach_use_case(repository)

        result = await use_case(
            AttachContactPointCommand(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value=" User@Example.COM ",
                is_primary=True,
            )
        )

        self.assertTrue(result.contact_point_created)
        self.assertTrue(result.binding_created)
        self.assertFalse(result.already_attached)
        self.assertEqual(repository.contact_point_saves, 1)
        self.assertEqual(repository.binding_saves, 1)
        contact_point = next(iter(repository.contact_points.values()))
        self.assertEqual(contact_point.normalized_value, "user@example.com")
        self.assertEqual(contact_point.hash_value, contact_point.hash_value.lower())
        binding = next(iter(repository.bindings.values()))
        self.assertTrue(binding.is_primary)
        self.assertTrue(binding.is_active)

    async def test_attach_reuses_existing_contact_point_and_is_idempotent(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        contact_point = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            now=now,
        )
        binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=contact_point.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=False,
        )
        repository.contact_points[contact_point.id] = contact_point
        repository.bindings[binding.id] = binding
        use_case = self._attach_use_case(repository)

        result = await use_case(
            AttachContactPointCommand(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="user@example.com",
                is_primary=False,
            )
        )

        self.assertFalse(result.contact_point_created)
        self.assertFalse(result.binding_created)
        self.assertTrue(result.already_attached)
        self.assertEqual(repository.contact_point_saves, 0)
        self.assertEqual(repository.binding_saves, 0)

    async def test_attach_reactivates_inactive_binding(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        contact_point = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            now=now,
        )
        binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=contact_point.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=False,
        )
        binding.detach(now=now)
        repository.contact_points[contact_point.id] = contact_point
        repository.bindings[binding.id] = binding
        use_case = self._attach_use_case(repository)

        result = await use_case(
            AttachContactPointCommand(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="user@example.com",
                is_primary=True,
            )
        )

        self.assertFalse(result.binding_created)
        self.assertFalse(result.already_attached)
        self.assertTrue(binding.is_active)
        self.assertTrue(binding.is_primary)
        self.assertIsNone(binding.detached_at)

    async def test_attach_fails_before_writes_when_owner_or_feature_invalid(
        self,
    ) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        repository = _Repository()
        owner_resolver = _OwnerResolver(exists=False)
        feature_gate = _FeatureGate()
        use_case = self._attach_use_case(repository, owner_resolver, feature_gate)

        with self.assertRaises(ContactPointOwnerNotFoundError):
            await use_case(
                AttachContactPointCommand(
                    tenant_id=tenant_id,
                    owner_object_id=owner_object_id,
                    owner_record_id=owner_record_id,
                    contact_point_type=ContactPointTypeVO.EMAIL,
                    raw_value="user@example.com",
                )
            )

        self.assertEqual(feature_gate.calls, [])
        self.assertEqual(repository.contact_point_saves, 0)
        self.assertEqual(repository.binding_saves, 0)

        repository = _Repository()
        feature_gate = _FeatureGate(ObjectFeatureNotEnabledError("disabled"))
        use_case = self._attach_use_case(repository, _OwnerResolver(), feature_gate)
        with self.assertRaises(ObjectFeatureNotEnabledError):
            await use_case(
                AttachContactPointCommand(
                    tenant_id=tenant_id,
                    owner_object_id=owner_object_id,
                    owner_record_id=owner_record_id,
                    contact_point_type=ContactPointTypeVO.EMAIL,
                    raw_value="user@example.com",
                )
            )
        self.assertEqual(repository.contact_point_saves, 0)
        self.assertEqual(repository.binding_saves, 0)

    async def test_primary_attach_unsets_existing_owner_type_primary(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        existing_point = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="old@example.com",
            now=now,
        )
        existing_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=existing_point.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=True,
        )
        repository.contact_points[existing_point.id] = existing_point
        repository.bindings[existing_binding.id] = existing_binding
        use_case = self._attach_use_case(repository)

        await use_case(
            AttachContactPointCommand(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="new@example.com",
                is_primary=True,
            )
        )

        self.assertFalse(existing_binding.is_primary)
        new_binding = [
            binding
            for binding in repository.bindings.values()
            if binding.id != existing_binding.id
        ][0]
        self.assertTrue(new_binding.is_primary)

    async def test_detach_soft_deactivates_and_promotes_next_primary(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        first_point = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="first@example.com",
            now=now,
        )
        second_point = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="second@example.com",
            now=now,
        )
        first = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=first_point.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=True,
        )
        second = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=second_point.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=False,
        )
        repository.contact_points[first_point.id] = first_point
        repository.contact_points[second_point.id] = second_point
        repository.bindings[first.id] = first
        repository.bindings[second.id] = second
        use_case = DetachContactPointUseCase(
            bindings=repository,
            clock=_Clock(now),
        )

        result = await use_case(
            DetachContactPointCommand(
                tenant_id=tenant_id,
                binding_id=first.id,
            )
        )

        self.assertTrue(result.binding_deleted)
        self.assertFalse(result.contact_point_deleted)
        self.assertTrue(result.contact_point_left_orphan)
        self.assertFalse(first.is_active)
        self.assertIsNotNone(first.detached_at)
        self.assertTrue(second.is_primary)


__all__ = [
    "ContactPointServicesTests",
    "ContactPointUseCaseTests",
]
