from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.repository import (
    ContactCommandRepositoryProtocol,
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO


class _FakeContactsStorage:
    def __init__(self) -> None:
        self._contacts: dict[UUID, ContactEntity] = {
            contact.id.value: contact for contact in self._build_seed_contacts()
        }

    @staticmethod
    def _build_seed_contacts() -> tuple[ContactEntity, ...]:
        return (
            ContactEntity.create(
                id_=ContactIdVO.from_value(uuid6.uuid7()),
                now=datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
                last_name="Smith",
                first_name="John",
                middle_name=None,
            ),
            ContactEntity.create(
                id_=ContactIdVO.from_value(uuid6.uuid7()),
                now=datetime(2026, 2, 5, 14, 30, tzinfo=UTC),
                last_name="Johnson",
                first_name="Emily",
                middle_name="Kate",
            ),
        )

    def get(self, contact_id: ContactIdVO) -> ContactEntity | None:
        return self._contacts.get(contact_id.value)

    def list(self, *, limit: int, offset: int) -> list[ContactEntity]:
        contacts = sorted(
            self._contacts.values(),
            key=lambda contact: (contact.created_at, str(contact.id.value)),
        )
        return contacts[offset : offset + limit]

    def save(self, contact: ContactEntity) -> ContactEntity:
        self._contacts[contact.id.value] = contact
        return contact

    def delete(self, contact_id: ContactIdVO) -> None:
        self._contacts.pop(contact_id.value, None)


_fake_contacts_storage = _FakeContactsStorage()


class FakeContactQueryRepository(ContactQueryRepositoryProtocol):
    def __init__(self, storage: _FakeContactsStorage) -> None:
        self._storage = storage

    async def get_by_id(self, *, contact_id: ContactIdVO) -> ContactEntity | None:
        return self._storage.get(contact_id)

    async def list(self, *, limit: int, offset: int) -> list[ContactEntity]:
        return self._storage.list(limit=limit, offset=offset)


class FakeContactCommandRepository(ContactCommandRepositoryProtocol):
    def __init__(self, storage: _FakeContactsStorage) -> None:
        self._storage = storage

    async def save(self, contact: ContactEntity) -> ContactEntity:
        return self._storage.save(contact)

    async def delete(self, contact_id: ContactIdVO) -> None:
        self._storage.delete(contact_id)


def get_fake_contacts_storage() -> _FakeContactsStorage:
    return _fake_contacts_storage


__all__ = [
    "FakeContactCommandRepository",
    "FakeContactQueryRepository",
    "get_fake_contacts_storage",
]
