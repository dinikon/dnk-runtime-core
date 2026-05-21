from __future__ import annotations

import unittest
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.crm.application.company.dto import (
    CompanyFieldDescriptionDTO,
    CompanyFieldsDescriptionDTO,
    CompanyObjectDescriptionDTO,
)
from src.modules.crm.presentation.http.company.controller.describe_company_fields import (
    describe_company_fields,
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


class _DescribeCompanyFieldsUseCaseStub:
    def __init__(self, result: CompanyFieldsDescriptionDTO) -> None:
        self.result = result
        self.tenant_id = None

    async def __call__(self, tenant_id: EntityIdVO) -> CompanyFieldsDescriptionDTO:
        self.tenant_id = tenant_id
        return self.result


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, tenant_id: EntityIdVO):
        raise self._exc


class CompanyFieldsControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_company_fields_response(self) -> None:
        object_id = uuid4()
        field_id = uuid4()
        use_case = _DescribeCompanyFieldsUseCaseStub(
            CompanyFieldsDescriptionDTO(
                object_description=CompanyObjectDescriptionDTO(
                    id=object_id,
                    singular_label="Company",
                    plural_label="Companies",
                    description="Tenant company registry.",
                    kind="standard",
                ),
                fields=(
                    CompanyFieldDescriptionDTO(
                        id=field_id,
                        field_name="legal_name",
                        label="Legal Name",
                        description="Company legal name.",
                        type="text",
                        kind="standard",
                        is_nullable=False,
                        default_value=None,
                        options=(),
                    ),
                ),
            )
        )
        context = _context()

        response = await describe_company_fields(
            context=context,
            use_case=use_case,
        )

        self.assertEqual(
            use_case.tenant_id,
            EntityIdVO.from_value(context.principal.tenant_id),
        )
        self.assertEqual(response.object.id, object_id)
        self.assertEqual(response.object.singular_label, "Company")
        self.assertEqual(response.object.plural_label, "Companies")
        self.assertEqual(response.object.kind, "standard")
        self.assertEqual(response.fields[0].id, field_id)
        self.assertEqual(response.fields[0].field_name, "legal_name")
        self.assertEqual(response.fields[0].type, "text")
        self.assertEqual(response.fields[0].kind, "standard")
        self.assertEqual(response.fields[0].options, [])

    async def test_returns_401_when_context_has_no_principal(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_company_fields(
                context=RequestContext(
                    principal=None,
                    request_id=None,
                    ip=None,
                    user_agent=None,
                ),
                use_case=_DescribeCompanyFieldsUseCaseStub(
                    CompanyFieldsDescriptionDTO(
                        object_description=CompanyObjectDescriptionDTO(
                            id=uuid4(),
                            singular_label="Company",
                            plural_label="Companies",
                            description="Tenant company registry.",
                        ),
                        fields=(),
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_returns_409_when_runtime_metadata_is_missing(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await describe_company_fields(
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="company",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)
