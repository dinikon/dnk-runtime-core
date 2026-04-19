from __future__ import annotations

import unittest
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.crm.application.contact.dto.contact_fields_description_dto import (
    ContactFieldDescriptionDTO,
    ContactFieldOptionDTO,
    ContactFieldsDescriptionDTO,
    ContactObjectDescriptionDTO,
)
from src.modules.crm.presentation.http.contact.controller.describe_contact_fields import (
    describe_contact_fields,
)
from src.modules.schema_registry.domain.error import RuntimeObjectNotFoundError
from src.modules.shared import EntityIdVO, Principal, RequestContext


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


class _DescribeContactFieldsUseCaseStub:
    def __init__(self, result: ContactFieldsDescriptionDTO) -> None:
        self.result = result
        self.tenant_id = None

    async def __call__(self, tenant_id: EntityIdVO) -> ContactFieldsDescriptionDTO:
        self.tenant_id = tenant_id
        return self.result


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, tenant_id: EntityIdVO):
        raise self._exc


class ContactFieldsControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_contact_fields_response(self) -> None:
        object_id = uuid4()
        field_id = uuid4()
        use_case = _DescribeContactFieldsUseCaseStub(
            ContactFieldsDescriptionDTO(
                object_description=ContactObjectDescriptionDTO(
                    id=object_id,
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Tenant contact registry.",
                ),
                fields=(
                    ContactFieldDescriptionDTO(
                        id=field_id,
                        field_name="status",
                        label="Status",
                        description="Contact status.",
                        type="select",
                        is_nullable=False,
                        default_value="'lead'",
                        options=(
                            ContactFieldOptionDTO(value="lead", label="Lead"),
                            ContactFieldOptionDTO(
                                value="customer",
                                label="Customer",
                            ),
                        ),
                    ),
                ),
            )
        )
        context = _context()

        response = await describe_contact_fields(
            context=context,
            use_case=use_case,
        )

        self.assertEqual(
            use_case.tenant_id,
            EntityIdVO.from_value(context.principal.tenant_id),
        )
        self.assertEqual(response.object.id, object_id)
        self.assertEqual(response.object.singular_label, "Contact")
        self.assertEqual(response.object.plural_label, "Contacts")
        self.assertEqual(response.fields[0].id, field_id)
        self.assertEqual(response.fields[0].field_name, "status")
        self.assertEqual(response.fields[0].type, "select")
        self.assertEqual(response.fields[0].default_value, "'lead'")
        self.assertEqual(
            [option.model_dump() for option in response.fields[0].options],
            [
                {"value": "lead", "label": "Lead"},
                {"value": "customer", "label": "Customer"},
            ],
        )

    async def test_returns_401_when_context_has_no_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_contact_fields(
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_DescribeContactFieldsUseCaseStub(
                    ContactFieldsDescriptionDTO(
                        object_description=ContactObjectDescriptionDTO(
                            id=uuid4(),
                            singular_label="Contact",
                            plural_label="Contacts",
                            description="Tenant contact registry.",
                        ),
                        fields=(),
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_returns_409_when_runtime_metadata_is_missing(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_contact_fields(
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="contact",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)
