from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from src.modules.crm.application.company.dto import CompanyDTO
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.presentation.http.company.controller.create_company import (
    create_company,
)
from src.modules.crm.presentation.http.company.controller.delete_company import (
    delete_company,
)
from src.modules.crm.presentation.http.company.controller.get_company import (
    get_company,
)
from src.modules.crm.presentation.http.company.controller.list_companies import (
    list_companies,
)
from src.modules.crm.presentation.http.company.controller.update_company import (
    update_company,
)
from src.modules.crm.presentation.http.company.requests import (
    CreateCompanyRequestSchema,
    UpdateCompanyRequestSchema,
)
from src.modules.runtime_data import (
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


class _UseCaseStub:
    def __init__(self, result) -> None:
        self.result = result
        self.command = None

    async def __call__(self, command):
        self.command = command
        return self.result


class _FailingUseCase:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, command):
        raise self._exc


class CompanyControllerErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_company_returns_response_shape(self) -> None:
        now = datetime.now(UTC)
        company_id = uuid4()
        use_case = _UseCaseStub(
            CompanyDTO(
                id=company_id,
                created_at=now,
                updated_at=now,
                legal_name="Acme LLC",
            )
        )

        response = await create_company(
            payload=CreateCompanyRequestSchema(legal_name="Acme LLC"),
            context=_context(),
            use_case=use_case,
        )

        self.assertEqual(response.id, company_id)
        self.assertEqual(response.created_at, now)
        self.assertEqual(response.updated_at, now)
        self.assertEqual(response.legal_name, "Acme LLC")
        self.assertEqual(use_case.command.legal_name, "Acme LLC")

    async def test_create_company_validation_error_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await create_company(
                payload=CreateCompanyRequestSchema(legal_name=""),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataValidationError("Field 'legal_name' must not be empty.")
                ),
            )

        self.assertEqual(
            caught.exception.status_code,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    async def test_update_company_persistence_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await update_company(
                company_id=uuid4(),
                payload=UpdateCompanyRequestSchema(legal_name="Acme Inc."),
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeDataPersistenceError(
                        "Runtime data persistence operation failed."
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_get_company_not_found_error_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await get_company(
                company_id=uuid4(),
                context=_context(),
                use_case=_FailingUseCase(CompanyNotFoundError("company-1")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)

    async def test_list_companies_schema_runtime_error_returns_409(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await list_companies(
                context=_context(),
                use_case=_FailingUseCase(
                    RuntimeObjectNotFoundError(
                        tenant_id=str(uuid4()),
                        object_name="company",
                    )
                ),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_409_CONFLICT)

    async def test_delete_company_not_found_error_returns_404(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await delete_company(
                company_id=uuid4(),
                context=_context(),
                use_case=_FailingUseCase(CompanyNotFoundError("company-1")),
            )

        self.assertEqual(caught.exception.status_code, status.HTTP_404_NOT_FOUND)
