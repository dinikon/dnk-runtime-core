from __future__ import annotations

import hashlib
import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.contact_point.application import (
    AttachContactPointCommand,
    AttachContactPointUseCase,
    ContactPointBindingDTO,
    ContactPointBindingListDTO,
    ContactPointDTO,
    ContactPointListDTO,
    DetachContactPointCommand,
    DetachContactPointUseCase,
    GetContactPointQuery,
    GetContactPointUseCase,
    ListContactPointBindingsQuery,
    ListContactPointBindingsUseCase,
    ListContactPointsQuery,
    ListContactPointsUseCase,
    ListOwnerContactPointsQuery,
    ListOwnerContactPointsUseCase,
    OwnerContactPointDTO,
    OwnerContactPointListDTO,
)
from src.modules.contact_point.domain import (
    ContactPointBindingEntity,
    ContactPointBindingIdVO,
    ContactPointEntity,
    ContactPointIdVO,
    ContactPointNotFoundError,
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


class _UuidGenerator:
    def __init__(self, values: list[UUID]) -> None:
        self.values = list(values)
        self.generated: list[UUID] = []

    def new_uuid(self) -> UUID:
        value = self.values.pop(0)
        self.generated.append(value)
        return value


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
        self.list_queries = []

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

    async def find_active_primary_by_owner_and_type(
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
            and binding.is_primary
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

    async def get_contact_point(self, query):
        contact_point = self.contact_points.get(query.contact_point_id)
        if contact_point is None:
            return None
        return ContactPointDTO(
            id=contact_point.id.uuid,
            created_at=contact_point.created_at,
            updated_at=contact_point.updated_at,
            contact_point_type=contact_point.contact_point_type,
            raw_value=contact_point.raw_value,
            normalized_value=contact_point.normalized_value,
        )

    async def list_contact_points(self, query):
        self.list_queries.append(query)
        contact_points = [
            contact_point
            for contact_point in self.contact_points.values()
            if query.contact_point_type is None
            or contact_point.contact_point_type == query.contact_point_type
        ]
        contact_points.sort(key=lambda item: (item.created_at, str(item.id)))
        page = contact_points[query.offset : query.offset + query.limit]
        items = tuple(
            ContactPointDTO(
                id=contact_point.id.uuid,
                created_at=contact_point.created_at,
                updated_at=contact_point.updated_at,
                contact_point_type=contact_point.contact_point_type,
                raw_value=contact_point.raw_value,
                normalized_value=contact_point.normalized_value,
            )
            for contact_point in page
        )
        return ContactPointListDTO(
            items=items,
            count=len(items),
            limit=query.limit,
            offset=query.offset,
        )

    async def list_owner_contact_points(self, query):
        self.list_queries.append(query)
        owner = OwnerContactPointBinding(
            owner_object_id=query.owner_object_id,
            owner_record_id=query.owner_record_id,
        )
        bindings = [
            binding
            for binding in self.bindings.values()
            if binding.owner == owner and binding.is_active
        ]
        if query.contact_point_type is not None:
            bindings = [
                binding
                for binding in bindings
                if binding.contact_point_type == query.contact_point_type
            ]
        bindings.sort(
            key=lambda item: (
                item.contact_point_type.value,
                not item.is_primary,
                item.created_at,
                str(item.id),
            )
        )
        if query.limit is not None:
            bindings = bindings[query.offset : query.offset + query.limit]
        items = []
        for binding in bindings:
            contact_point = self.contact_points[binding.contact_point_id]
            items.append(
                OwnerContactPointDTO(
                    binding_id=binding.id.uuid,
                    contact_point_id=contact_point.id.uuid,
                    contact_point_type=contact_point.contact_point_type,
                    raw_value=contact_point.raw_value,
                    normalized_value=contact_point.normalized_value,
                    is_primary=binding.is_primary,
                    is_active=binding.is_active,
                    detached_at=binding.detached_at,
                    created_at=binding.created_at,
                    updated_at=binding.updated_at,
                )
            )
        return OwnerContactPointListDTO(
            items=tuple(items),
            count=len(items),
            limit=query.limit,
            offset=query.offset,
        )

    async def list_contact_point_bindings(self, query):
        self.list_queries.append(query)
        bindings = list(self.bindings.values())
        if query.contact_point_type is not None:
            bindings = [
                binding
                for binding in bindings
                if binding.contact_point_type == query.contact_point_type
            ]
        if query.contact_point_id is not None:
            bindings = [
                binding
                for binding in bindings
                if binding.contact_point_id == query.contact_point_id
            ]
        if query.owner_object_id is not None:
            bindings = [
                binding
                for binding in bindings
                if binding.owner.owner_object_id == query.owner_object_id
            ]
        if query.owner_record_id is not None:
            bindings = [
                binding
                for binding in bindings
                if binding.owner.owner_record_id == query.owner_record_id
            ]
        if query.is_active is not None:
            bindings = [
                binding for binding in bindings if binding.is_active == query.is_active
            ]
        bindings.sort(key=lambda item: (item.created_at, str(item.id)))
        page = bindings[query.offset : query.offset + query.limit]
        items = tuple(
            ContactPointBindingDTO(
                id=binding.id.uuid,
                contact_point_id=binding.contact_point_id.uuid,
                contact_point_type=binding.contact_point_type,
                owner_object_id=binding.owner.owner_object_id.uuid,
                owner_record_id=binding.owner.owner_record_id.uuid,
                is_primary=binding.is_primary,
                is_active=binding.is_active,
                detached_at=binding.detached_at,
                created_at=binding.created_at,
                updated_at=binding.updated_at,
            )
            for binding in page
        )
        return ContactPointBindingListDTO(
            items=items,
            count=len(items),
            limit=query.limit,
            offset=query.offset,
        )


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
            raw_value="+380671112233",
        )
        international_phone = normalizer.normalize(
            contact_point_type=ContactPointTypeVO.PHONE,
            raw_value="+1 (415) 555-2671",
        )

        self.assertEqual(email, "user@example.com")
        self.assertEqual(phone, "+380671112233")
        self.assertEqual(international_phone, "+14155552671")
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
        for raw_value in (
            "0671112233",
            "+999123456789",
            "+1 (415) 555-2671 ext. 123",
        ):
            with self.subTest(raw_value=raw_value):
                with self.assertRaises(InvalidContactPointValueError):
                    normalizer.normalize(
                        contact_point_type=ContactPointTypeVO.PHONE,
                        raw_value=raw_value,
                    )


class ContactPointUseCaseTests(unittest.IsolatedAsyncioTestCase):

    def _attach_use_case(
        self,
        repository: _Repository,
        owner_resolver: _OwnerResolver | None = None,
        feature_gate: _FeatureGate | None = None,
        now: datetime | None = None,
        uuid_generator: _UuidGenerator | None = None,
    ) -> AttachContactPointUseCase:
        return AttachContactPointUseCase(
            contact_points=repository,
            bindings=repository,
            owner_resolver=owner_resolver or _OwnerResolver(),
            feature_gate=feature_gate or _FeatureGate(),
            normalizer=ContactPointNormalizeService(),
            hash_service=ContactPointHashService(),
            uuid_generator=uuid_generator
            or _UuidGenerator([uuid4(), uuid4(), uuid4(), uuid4()]),
            clock=_Clock(now or datetime(2026, 5, 21, 10, 0, tzinfo=UTC)),
        )

    @staticmethod
    def _get_use_case(repository: _Repository) -> GetContactPointUseCase:
        return GetContactPointUseCase(query_repository=repository)

    @staticmethod
    def _list_contact_points_use_case(
        repository: _Repository,
    ) -> ListContactPointsUseCase:
        return ListContactPointsUseCase(query_repository=repository)

    @staticmethod
    def _list_bindings_use_case(
        repository: _Repository,
    ) -> ListContactPointBindingsUseCase:
        return ListContactPointBindingsUseCase(query_repository=repository)

    @staticmethod
    def _list_use_case(
        repository: _Repository,
        owner_resolver: _OwnerResolver | None = None,
        feature_gate: _FeatureGate | None = None,
    ) -> ListOwnerContactPointsUseCase:
        return ListOwnerContactPointsUseCase(
            query_repository=repository,
            owner_resolver=owner_resolver or _OwnerResolver(),
            feature_gate=feature_gate or _FeatureGate(),
        )

    async def test_attach_creates_contact_point_and_binding(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        repository = _Repository()
        contact_point_uuid = uuid4()
        binding_uuid = uuid4()
        uuid_generator = _UuidGenerator([contact_point_uuid, binding_uuid])
        use_case = self._attach_use_case(
            repository,
            uuid_generator=uuid_generator,
        )

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
        self.assertEqual(result.contact_point_id, contact_point_uuid)
        self.assertEqual(result.binding_id, binding_uuid)
        self.assertEqual(uuid_generator.generated, [contact_point_uuid, binding_uuid])
        self.assertEqual(repository.contact_point_saves, 1)
        self.assertEqual(repository.binding_saves, 1)
        contact_point = next(iter(repository.contact_points.values()))
        self.assertEqual(contact_point.normalized_value, "user@example.com")
        self.assertEqual(contact_point.hash_value, contact_point.hash_value.lower())
        binding = next(iter(repository.bindings.values()))
        self.assertTrue(binding.is_primary)
        self.assertTrue(binding.is_active)

    async def test_get_contact_point_returns_dto_without_hash(self) -> None:
        tenant_id, _, _ = _ids()
        repository = _Repository()
        contact_point = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="user@example.com",
        )
        repository.contact_points[contact_point.id] = contact_point
        use_case = self._get_use_case(repository)

        result = await use_case(
            GetContactPointQuery(
                tenant_id=tenant_id,
                contact_point_id=contact_point.id,
            )
        )

        self.assertEqual(result.id, contact_point.id.uuid)
        self.assertEqual(result.raw_value, "user@example.com")
        self.assertFalse(hasattr(result, "hash_value"))
        self.assertFalse(hasattr(result, "normalized_hash"))

    async def test_get_contact_point_raises_when_missing(self) -> None:
        tenant_id, _, _ = _ids()
        use_case = self._get_use_case(_Repository())

        with self.assertRaises(ContactPointNotFoundError):
            await use_case(
                GetContactPointQuery(
                    tenant_id=tenant_id,
                    contact_point_id=ContactPointIdVO.from_value(uuid4()),
                )
            )

    async def test_list_contact_points_forwards_type_filter_and_pagination(
        self,
    ) -> None:
        tenant_id, _, _ = _ids()
        repository = _Repository()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        email = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="user@example.com",
            now=now,
        )
        phone = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            contact_point_type=ContactPointTypeVO.PHONE,
            value="+380671112233",
            now=now,
        )
        repository.contact_points[email.id] = email
        repository.contact_points[phone.id] = phone
        use_case = self._list_contact_points_use_case(repository)

        result = await use_case(
            ListContactPointsQuery(
                tenant_id=tenant_id,
                contact_point_type=ContactPointTypeVO.PHONE,
                limit=10,
                offset=0,
            )
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.items[0].id, phone.id.uuid)
        self.assertEqual(
            repository.list_queries[0].contact_point_type, ContactPointTypeVO.PHONE
        )
        self.assertEqual(repository.list_queries[0].limit, 10)

    async def test_list_owner_contact_points_returns_active_items_in_order(
        self,
    ) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        email_primary = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="primary@example.com",
            now=now,
        )
        email_secondary = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="secondary@example.com",
            now=now,
        )
        phone = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            contact_point_type=ContactPointTypeVO.PHONE,
            value="+380671112233",
            now=now,
        )
        inactive = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="inactive@example.com",
            now=now,
        )
        repository.contact_points[email_primary.id] = email_primary
        repository.contact_points[email_secondary.id] = email_secondary
        repository.contact_points[phone.id] = phone
        repository.contact_points[inactive.id] = inactive

        secondary_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=email_secondary.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=False,
        )
        primary_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=email_primary.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=True,
        )
        phone_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=phone.id,
            contact_point_type=ContactPointTypeVO.PHONE,
            owner=owner,
            is_primary=True,
        )
        inactive_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=inactive.id,
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=False,
        )
        inactive_binding.detach(now=now)
        repository.bindings[secondary_binding.id] = secondary_binding
        repository.bindings[primary_binding.id] = primary_binding
        repository.bindings[phone_binding.id] = phone_binding
        repository.bindings[inactive_binding.id] = inactive_binding
        use_case = self._list_use_case(repository)

        result = await use_case(
            ListOwnerContactPointsQuery(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
            )
        )

        self.assertEqual(result.count, 3)
        self.assertEqual(
            [item.contact_point_id for item in result.items],
            [email_primary.id.uuid, email_secondary.id.uuid, phone.id.uuid],
        )
        self.assertEqual(result.items[0].binding_id, primary_binding.id.uuid)
        self.assertTrue(result.items[0].is_primary)
        self.assertTrue(result.items[0].is_active)
        self.assertIsNone(result.items[0].detached_at)
        self.assertEqual(result.items[0].raw_value, "primary@example.com")
        self.assertEqual(result.items[0].created_at, primary_binding.created_at)

    async def test_list_owner_contact_points_supports_type_filter(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        email = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="user@example.com",
            now=now,
        )
        phone = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            contact_point_type=ContactPointTypeVO.PHONE,
            value="+380671112233",
            now=now,
        )
        repository.contact_points[email.id] = email
        repository.contact_points[phone.id] = phone
        repository.bindings[ContactPointBindingIdVO.from_value(uuid4())] = (
            ContactPointBindingEntity.create(
                id_=ContactPointBindingIdVO.from_value(uuid4()),
                now=now,
                contact_point_id=email.id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                owner=owner,
                is_primary=True,
            )
        )
        phone_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=phone.id,
            contact_point_type=ContactPointTypeVO.PHONE,
            owner=owner,
            is_primary=True,
        )
        repository.bindings[phone_binding.id] = phone_binding
        use_case = self._list_use_case(repository)

        result = await use_case(
            ListOwnerContactPointsQuery(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                contact_point_type=ContactPointTypeVO.PHONE,
                limit=50,
                offset=0,
            )
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.items[0].contact_point_id, phone.id.uuid)
        self.assertEqual(
            repository.list_queries[0].contact_point_type, ContactPointTypeVO.PHONE
        )

    async def test_list_owner_contact_points_returns_empty_list(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        repository = _Repository()
        use_case = self._list_use_case(repository)

        result = await use_case(
            ListOwnerContactPointsQuery(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
            )
        )

        self.assertEqual(result.items, ())
        self.assertEqual(result.count, 0)

    async def test_list_contact_point_bindings_supports_filters(self) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        other_owner = EntityIdVO.from_value(uuid4())
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        active_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            contact_point_type=ContactPointTypeVO.EMAIL,
            owner=owner,
            is_primary=True,
        )
        inactive_binding = ContactPointBindingEntity.create(
            id_=ContactPointBindingIdVO.from_value(uuid4()),
            now=now,
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            contact_point_type=ContactPointTypeVO.PHONE,
            owner=OwnerContactPointBinding(other_owner, owner_record_id),
            is_primary=False,
        )
        inactive_binding.detach(now=now)
        repository.bindings[active_binding.id] = active_binding
        repository.bindings[inactive_binding.id] = inactive_binding
        use_case = self._list_bindings_use_case(repository)

        result = await use_case(
            ListContactPointBindingsQuery(
                tenant_id=tenant_id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                is_active=True,
                limit=20,
                offset=0,
            )
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.items[0].id, active_binding.id.uuid)
        self.assertTrue(result.items[0].is_active)
        self.assertEqual(repository.list_queries[0].owner_object_id, owner_object_id)
        self.assertEqual(repository.list_queries[0].is_active, True)

    async def test_list_owner_contact_points_fails_before_query_when_guard_invalid(
        self,
    ) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        repository = _Repository()
        owner_resolver = _OwnerResolver(exists=False)
        use_case = self._list_use_case(repository, owner_resolver=owner_resolver)

        with self.assertRaises(ContactPointOwnerNotFoundError):
            await use_case(
                ListOwnerContactPointsQuery(
                    tenant_id=tenant_id,
                    owner_object_id=owner_object_id,
                    owner_record_id=owner_record_id,
                )
            )

        self.assertEqual(repository.list_queries, [])

        feature_gate = _FeatureGate(ObjectFeatureNotEnabledError("disabled"))
        use_case = self._list_use_case(repository, feature_gate=feature_gate)
        with self.assertRaises(ObjectFeatureNotEnabledError):
            await use_case(
                ListOwnerContactPointsQuery(
                    tenant_id=tenant_id,
                    owner_object_id=owner_object_id,
                    owner_record_id=owner_record_id,
                )
            )

        self.assertEqual(repository.list_queries, [])

    async def test_first_attach_for_owner_type_becomes_primary_when_request_false(
        self,
    ) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        repository = _Repository()
        use_case = self._attach_use_case(repository)

        await use_case(
            AttachContactPointCommand(
                tenant_id=tenant_id,
                owner_object_id=owner_object_id,
                owner_record_id=owner_record_id,
                contact_point_type=ContactPointTypeVO.EMAIL,
                raw_value="first@example.com",
                is_primary=False,
            )
        )

        binding = next(iter(repository.bindings.values()))
        self.assertTrue(binding.is_primary)

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
            is_primary=True,
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

    async def test_second_attach_for_owner_type_stays_non_primary_when_primary_exists(
        self,
    ) -> None:
        tenant_id, owner_object_id, owner_record_id = _ids()
        now = datetime(2026, 5, 21, 10, 0, tzinfo=UTC)
        owner = OwnerContactPointBinding(owner_object_id, owner_record_id)
        repository = _Repository()
        existing_point = _contact_point(
            contact_point_id=ContactPointIdVO.from_value(uuid4()),
            value="primary@example.com",
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
                raw_value="secondary@example.com",
                is_primary=False,
            )
        )

        new_binding = [
            binding
            for binding in repository.bindings.values()
            if binding.id != existing_binding.id
        ][0]
        self.assertTrue(existing_binding.is_primary)
        self.assertFalse(new_binding.is_primary)

    async def test_active_existing_non_primary_becomes_primary_when_primary_missing(
        self,
    ) -> None:
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

        self.assertTrue(result.already_attached)
        self.assertTrue(binding.is_primary)
        self.assertEqual(repository.binding_saves, 1)

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
                is_primary=False,
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

    async def test_detach_non_primary_promotes_when_primary_is_missing(self) -> None:
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
            is_primary=False,
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

        await use_case(
            DetachContactPointCommand(
                tenant_id=tenant_id,
                binding_id=first.id,
            )
        )

        self.assertFalse(first.is_active)
        self.assertTrue(second.is_primary)

    async def test_detach_last_active_binding_does_not_promote(self) -> None:
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
            is_primary=True,
        )
        repository.contact_points[contact_point.id] = contact_point
        repository.bindings[binding.id] = binding
        use_case = DetachContactPointUseCase(
            bindings=repository,
            clock=_Clock(now),
        )

        result = await use_case(
            DetachContactPointCommand(
                tenant_id=tenant_id,
                binding_id=binding.id,
            )
        )

        self.assertTrue(result.contact_point_left_orphan)
        self.assertFalse(binding.is_active)
        self.assertFalse(binding.is_primary)


__all__ = [
    "ContactPointServicesTests",
    "ContactPointUseCaseTests",
]
