from __future__ import annotations

import unittest
from uuid import uuid4
from datetime import UTC, datetime

from fastapi import HTTPException, status

from src.modules.crm.application.contact.dto import ContactDTO, ContactListResultDTO
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.presentation.http.contact.controller.create_contact import (
    create_contact,
)
from src.modules.crm.presentation.http.contact.controller.delete_contact import (
    delete_contact,
)
from src.modules.crm.presentation.http.contact.controller.get_contact import (
    get_contact,
)
from src.modules.crm.presentation.http.contact.controller.list_contacts import (
    list_contacts,
    search_contacts,
)
from src.modules.crm.presentation.http.contact.controller.update_contact import (
    update_contact,
)
from src.modules.crm.presentation.http.contact.requests import (
    ContactSearchRequestSchema,
    CreateContactRequestSchema,
    UpdateContactRequestSchema,
)
from src.modules.runtime_data import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import RuntimeObjectNotFoundError
from src.modules.shared import Principal, RequestContext


def _context() -> RequestContext:
    return RequestContext(
        principal=Principal(
            user_id=str(uuid4()),
            tenant_id=str(uuid4()),
            session_id=str(uuid4()),
            roles=(),
        ),
        request_id=None,
        ip=None,
        user_agent=None,
    )


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, command):
        raise self._exc


class ContactControllerErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_contact_validation_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_contact(
                payload=CreateContactRequestSchema(
                    first_name="Jane",
                    status="lead",
                    tags=["unknown"],
                ),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataValidationError(
                        "Field 'tags' has unsupported option 'unknown'."
                    )
                ),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_update_contact_persistence_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await update_contact(
                contact_id=uuid4(),
                payload=UpdateContactRequestSchema(
                    first_name="Jane",
                    tags=["vip"],
                ),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataPersistenceError(
                        "Runtime data persistence operation failed."
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_get_contact_not_found_error_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await get_contact(
                contact_id=uuid4(),
                context=_context(),
                use_case=_FailingUseCase(ContactNotFoundError("contact-1")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)

    async def test_list_contacts_schema_runtime_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_contacts(
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="contact",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_search_contacts_passes_raw_dsl_and_returns_total(self) -> None:
        context = _context()
        contact_id = uuid4()
        now = datetime.now(UTC)
        recorded_query = None

        class UseCaseStub:
            async def __call__(self, query):
                nonlocal recorded_query
                recorded_query = query
                return ContactListResultDTO(
                    items=(
                        ContactDTO(
                            id=contact_id,
                            created_at=now,
                            updated_at=now,
                            last_name="Doe",
                            first_name="Jane",
                            middle_name=None,
                            status="lead",
                            tags=["vip"],
                        ),
                    ),
                    total=7,
                    limit=query.limit,
                    offset=query.offset,
                )

        payload = ContactSearchRequestSchema(
            filter={"field": "status", "op": "eq", "value": "lead"},
            sort=[{"field": "created_at", "direction": "desc"}],
            pagination={"limit": 10, "offset": 5},
        )

        response = await search_contacts(
            payload=payload,
            context=context,
            use_case=UseCaseStub(),
        )

        self.assertEqual(recorded_query.filter_dsl, payload.filter)
        self.assertEqual(recorded_query.sort_dsl, payload.sort)
        self.assertEqual(response.pagination.total, 7)
        self.assertEqual(response.data[0].id, contact_id)

    async def test_search_contacts_runtime_filter_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await search_contacts(
                payload=ContactSearchRequestSchema(
                    filter={"field": "status", "op": "contains", "value": "lead"},
                    sort=[],
                    pagination={"limit": 10, "offset": 0},
                ),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataFilterError(
                        "UNSUPPORTED_OPERATOR_FOR_FIELD_TYPE: bad operator"
                    )
                ),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_delete_contact_not_found_error_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await delete_contact(
                contact_id=uuid4(),
                context=_context(),
                use_case=_FailingUseCase(ContactNotFoundError("contact-1")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)
