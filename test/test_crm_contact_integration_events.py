from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.crm.application.contact.integration_events import (
    CRM_CONTACT_CREATED,
    CRM_CONTACT_DELETED,
    CRM_CONTACT_UPDATED,
    contact_created_event,
    contact_deleted_event,
    contact_updated_event,
)


class CrmContactIntegrationEventTests(unittest.TestCase):
    def test_contact_created_event_uses_crm_contact_metadata(self) -> None:
        tenant_id = uuid4()
        contact_id = uuid4()
        actor_id = uuid4()
        occurred_at = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)

        event = contact_created_event(
            tenant_id=tenant_id,
            contact_id=contact_id,
            occurred_at=occurred_at,
            actor_id=actor_id,
            payload={
                "first_name": "Jane",
                "last_name": "Doe",
                "middle_name": None,
                "status": "lead",
                "tags": ["vip"],
            },
        )

        self.assertEqual(event.tenant_id, tenant_id)
        self.assertEqual(event.event_type, CRM_CONTACT_CREATED)
        self.assertEqual(event.event_version, 1)
        self.assertEqual(event.aggregate_type, "crm.contact")
        self.assertEqual(event.aggregate_id, contact_id)
        self.assertEqual(event.occurred_at, occurred_at)
        self.assertEqual(event.payload["contact_id"], str(contact_id))
        self.assertEqual(event.payload["actor_id"], str(actor_id))
        self.assertEqual(event.payload["data"]["first_name"], "Jane")

    def test_contact_updated_event_includes_changed_fields(self) -> None:
        tenant_id = uuid4()
        contact_id = uuid4()
        occurred_at = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)

        event = contact_updated_event(
            tenant_id=tenant_id,
            contact_id=contact_id,
            occurred_at=occurred_at,
            changed_fields=["status"],
            before={"status": "lead"},
            after={"status": "customer"},
        )

        self.assertEqual(event.event_type, CRM_CONTACT_UPDATED)
        self.assertEqual(event.event_version, 1)
        self.assertEqual(event.aggregate_type, "crm.contact")
        self.assertEqual(event.aggregate_id, contact_id)
        self.assertEqual(event.payload["contact_id"], str(contact_id))
        self.assertIsNone(event.payload["actor_id"])
        self.assertEqual(event.payload["changed_fields"], ["status"])
        self.assertEqual(event.payload["before"], {"status": "lead"})
        self.assertEqual(event.payload["after"], {"status": "customer"})

    def test_contact_deleted_event_includes_reason(self) -> None:
        tenant_id = uuid4()
        contact_id = uuid4()
        actor_id = uuid4()
        occurred_at = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)

        event = contact_deleted_event(
            tenant_id=tenant_id,
            contact_id=contact_id,
            occurred_at=occurred_at,
            actor_id=actor_id,
            reason="merged",
        )

        self.assertEqual(event.event_type, CRM_CONTACT_DELETED)
        self.assertEqual(event.event_version, 1)
        self.assertEqual(event.aggregate_type, "crm.contact")
        self.assertEqual(event.aggregate_id, contact_id)
        self.assertEqual(event.payload["contact_id"], str(contact_id))
        self.assertEqual(event.payload["actor_id"], str(actor_id))
        self.assertEqual(event.payload["reason"], "merged")


__all__ = ["CrmContactIntegrationEventTests"]
