from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.crm.application.company.query.repository import (
        CompanyQueryRepositoryProtocol,
    )

from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.crm.domain.links import CompanyContactLinksPolicy
from src.modules.shared.domain.time import ClockPort


class CompanyContactsService:
    """Coordinate Contact aggregates inside the caller's existing transaction."""

    def __init__(
        self,
        contacts: ContactRepositoryProtocol,
        queries: CompanyQueryRepositoryProtocol,
        clock: ClockPort,
    ):
        self.contacts, self.queries, self.clock = contacts, queries, clock

    async def lock_contacts(self, tenant_id, *, requested, expected):
        CompanyContactLinksPolicy.changes(
            current=expected or (), expected=expected, requested=requested
        )
        contacts = await self.contacts.get_many(
            tenant_id, tuple(set(requested) | set(expected)), for_update=True
        )
        CompanyContactLinksPolicy.ensure_available(
            available=tuple(contact.id for contact in contacts),
            requested=requested,
            expected=expected,
        )
        return {contact.id: contact for contact in contacts}

    async def apply(
        self, tenant_id, company_id, actor_id, *, requested, expected, contacts
    ):
        current = await self.queries.linked_contact_ids(tenant_id, company_id)
        added, removed = CompanyContactLinksPolicy.changes(
            current=current, expected=expected, requested=requested
        )
        now = self.clock.now()
        for identifier in sorted(added | removed, key=lambda value: value.uuid):
            contact = contacts[identifier]
            if identifier in added:
                contact.link_company(company_id, actor_id=actor_id, now=now)
            else:
                contact.unlink_company(company_id, actor_id=actor_id, now=now)
            await self.contacts.save(tenant_id, contact)
