from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.crm.application import (
    CreateCompanyCommand,
    CreateContactCommand,
    DeleteCompanyCommand,
    DeleteContactCommand,
    GetCompanyQuery,
    GetContactQuery,
    ListCompaniesQuery,
    ListContactsQuery,
    UpdateCompanyCommand,
    UpdateContactCommand,
)
from src.modules.crm.application.dto import CompanyDTO, ContactDTO
from src.modules.crm.domain.errors import CompanyNotFoundError, ContactNotFoundError
from src.modules.crm.presentation.depends.application import (
    CreateCompanyUseCaseDep,
    CreateContactUseCaseDep,
    DeleteCompanyUseCaseDep,
    DeleteContactUseCaseDep,
    GetCompanyUseCaseDep,
    GetContactUseCaseDep,
    ListCompaniesUseCaseDep,
    ListContactsUseCaseDep,
    UpdateCompanyUseCaseDep,
    UpdateContactUseCaseDep,
)
from src.modules.crm.presentation.http.requests import (
    CreateCompanyRequestSchema,
    CreateContactRequestSchema,
    UpdateCompanyRequestSchema,
    UpdateContactRequestSchema,
)
from src.modules.crm.presentation.http.responses import (
    CompanyResponseSchema,
    ContactResponseSchema,
)
from src.modules.runtime_record.domain.errors import (
    RuntimeDataSourceNotFoundError,
    RuntimeObjectNotFoundError,
    RuntimeRecordNotFoundError,
    RuntimeRecordValidationError,
)
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/crm", tags=["crm"])


@router.post(
    "/tenants/{tenant_id}/contacts",
    response_model=ContactResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    tenant_id: UUID,
    payload: CreateContactRequestSchema,
    use_case: CreateContactUseCaseDep,
) -> ContactResponseSchema:
    try:
        result = await use_case.execute(
            CreateContactCommand(
                last_name=payload.last_name,
                first_name=payload.first_name,
                middle_name=payload.middle_name,
                tenant_id=tenant_id,
                custom_fields=dict(payload.custom_fields),
            )
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return _contact_to_response(result)


@router.get(
    "/tenants/{tenant_id}/contacts/{contact_id}",
    response_model=ContactResponseSchema,
)
async def get_contact(
    tenant_id: UUID,
    contact_id: UUID,
    use_case: GetContactUseCaseDep,
) -> ContactResponseSchema:
    try:
        result = await use_case.execute(
            GetContactQuery(
                contact_id=contact_id,
                tenant_id=tenant_id,
            )
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return _contact_to_response(result)


@router.get(
    "/tenants/{tenant_id}/contacts",
    response_model=list[ContactResponseSchema],
)
async def list_contacts(
    tenant_id: UUID,
    use_case: ListContactsUseCaseDep,
) -> list[ContactResponseSchema]:
    try:
        results = await use_case.execute(ListContactsQuery(tenant_id=tenant_id))
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return [_contact_to_response(item) for item in results]


@router.patch(
    "/tenants/{tenant_id}/contacts/{contact_id}",
    response_model=ContactResponseSchema,
)
async def update_contact(
    tenant_id: UUID,
    contact_id: UUID,
    payload: UpdateContactRequestSchema,
    use_case: UpdateContactUseCaseDep,
) -> ContactResponseSchema:
    try:
        result = await use_case.execute(
            UpdateContactCommand(
                contact_id=contact_id,
                last_name=payload.last_name,
                first_name=payload.first_name,
                middle_name=payload.middle_name,
                tenant_id=tenant_id,
                custom_fields=dict(payload.custom_fields),
            )
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return _contact_to_response(result)


@router.delete(
    "/tenants/{tenant_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    tenant_id: UUID,
    contact_id: UUID,
    use_case: DeleteContactUseCaseDep,
) -> Response:
    _ = tenant_id
    try:
        await use_case.execute(DeleteContactCommand(contact_id=contact_id))
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/tenants/{tenant_id}/companies",
    response_model=CompanyResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_company(
    tenant_id: UUID,
    payload: CreateCompanyRequestSchema,
    use_case: CreateCompanyUseCaseDep,
) -> CompanyResponseSchema:
    try:
        result = await use_case.execute(
            CreateCompanyCommand(
                last_name=payload.last_name,
                company_name=payload.company_name,
                tenant_id=tenant_id,
                custom_fields=dict(payload.custom_fields),
            )
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return _company_to_response(result)


@router.get(
    "/tenants/{tenant_id}/companies/{company_id}",
    response_model=CompanyResponseSchema,
)
async def get_company(
    tenant_id: UUID,
    company_id: UUID,
    use_case: GetCompanyUseCaseDep,
) -> CompanyResponseSchema:
    try:
        result = await use_case.execute(
            GetCompanyQuery(
                company_id=company_id,
                tenant_id=tenant_id,
            )
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return _company_to_response(result)


@router.get(
    "/tenants/{tenant_id}/companies",
    response_model=list[CompanyResponseSchema],
)
async def list_companies(
    tenant_id: UUID,
    use_case: ListCompaniesUseCaseDep,
) -> list[CompanyResponseSchema]:
    try:
        results = await use_case.execute(ListCompaniesQuery(tenant_id=tenant_id))
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return [_company_to_response(item) for item in results]


@router.patch(
    "/tenants/{tenant_id}/companies/{company_id}",
    response_model=CompanyResponseSchema,
)
async def update_company(
    tenant_id: UUID,
    company_id: UUID,
    payload: UpdateCompanyRequestSchema,
    use_case: UpdateCompanyUseCaseDep,
) -> CompanyResponseSchema:
    try:
        result = await use_case.execute(
            UpdateCompanyCommand(
                company_id=company_id,
                last_name=payload.last_name,
                company_name=payload.company_name,
                tenant_id=tenant_id,
                custom_fields=dict(payload.custom_fields),
            )
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)

    return _company_to_response(result)


@router.delete(
    "/tenants/{tenant_id}/companies/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_company(
    tenant_id: UUID,
    company_id: UUID,
    use_case: DeleteCompanyUseCaseDep,
) -> Response:
    _ = tenant_id
    try:
        await use_case.execute(DeleteCompanyCommand(company_id=company_id))
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "crm"}


def _contact_to_response(dto: ContactDTO) -> ContactResponseSchema:
    return ContactResponseSchema(
        id=dto.id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        last_name=dto.last_name,
        first_name=dto.first_name,
        middle_name=dto.middle_name,
        custom_fields=dict(dto.custom_fields),
    )


def _company_to_response(dto: CompanyDTO) -> CompanyResponseSchema:
    return CompanyResponseSchema(
        id=dto.id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        last_name=dto.last_name,
        company_name=dto.company_name,
        custom_fields=dict(dto.custom_fields),
    )


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, (ContactNotFoundError, CompanyNotFoundError, RuntimeRecordNotFoundError)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, (RuntimeObjectNotFoundError, RuntimeDataSourceNotFoundError)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, (DomainError, RuntimeRecordValidationError, ValueError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error.",
    ) from exc


__all__ = ["router"]
