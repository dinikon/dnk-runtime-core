from uuid import UUID

from fastapi import HTTPException, Response
from sqlalchemy.exc import IntegrityError

from src.modules.crm.application.contact.command.create_contact.command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.command.delete_contact.command import (
    DeleteContactCommand,
)
from src.modules.crm.application.contact.command.update_contact.command import (
    UpdateContactCommand,
)
from src.modules.crm.application.contact.query.get_contact.query import GetContactQuery
from src.modules.crm.application.contact.query.list_contacts.query import (
    ListContactsQuery,
)
from src.modules.crm.domain.contact.error import (
    ContactNotFoundError,
    InvalidContactNameError,
)
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import (
    CreateContactHandlerDep,
    DeleteContactHandlerDep,
    GetContactHandlerDep,
    ListContactsHandlerDep,
    UpdateContactHandlerDep,
)
from src.modules.crm.presentation.contact.http.request import (
    CreateContactRequest,
    PatchContactRequest,
    PutContactRequest,
)
from src.modules.crm.presentation.contact.http.response import (
    CreateContactResponse,
    GetContactResponse,
    UpdateContactResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


async def create_contact(
    payload: CreateContactRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateContactHandlerDep,
) -> CreateContactResponse:
    """Создаёт контакт в tenant аутентифицированного участника."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    command = CreateContactCommand(
        actor_id=EntityIdVO.from_value(principal.user_id),
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
    )
    try:
        result = await handler.execute(command)
    except InvalidContactNameError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        # asyncpg сохраняет имя ограничения в исходной причине DBAPI-ошибки.
        if (
            getattr(exc.orig, "sqlstate", None) == "23505"
            and getattr(exc.orig.__cause__, "constraint_name", None) == "pk_contacts"
        ):
            raise HTTPException(409, "Contact identifier already exists.") from exc
        raise
    return CreateContactResponse.from_dto(result)


async def get_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetContactHandlerDep,
) -> GetContactResponse:
    """Возвращает конкретный контакт только из tenant текущего участника."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    query = GetContactQuery(
        contact_id=ContactIdVO.from_value(contact_id),
    )
    try:
        result = await handler.execute(query)
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetContactResponse.from_dto(result)


async def list_contacts(
    context: AuthenticatedRequestContextDep,
    handler: ListContactsHandlerDep,
) -> list[GetContactResponse]:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    result = await handler.execute(ListContactsQuery())
    return [GetContactResponse.from_dto(contact) for contact in result.contacts]


async def _update_contact(
    contact_id: UUID,
    payload: PutContactRequest | PatchContactRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateContactHandlerDep,
    fields: frozenset[str],
) -> UpdateContactResponse:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    command = UpdateContactCommand(
        contact_id=ContactIdVO.from_value(contact_id),
        actor_id=EntityIdVO.from_value(principal.user_id),
        fields=fields,
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
    )
    try:
        result = await handler.execute(command)
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidContactNameError as exc:
        raise HTTPException(422, str(exc)) from exc
    return UpdateContactResponse.from_dto(result)


async def put_contact(
    contact_id: UUID,
    payload: PutContactRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateContactHandlerDep,
) -> UpdateContactResponse:
    """Полностью заменяет ФИО контакта."""
    return await _update_contact(
        contact_id,
        payload,
        context,
        handler,
        frozenset(("first_name", "last_name", "middle_name")),
    )


async def patch_contact(
    contact_id: UUID,
    payload: PatchContactRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateContactHandlerDep,
) -> UpdateContactResponse:
    """Обновляет только переданные части ФИО."""
    return await _update_contact(
        contact_id, payload, context, handler, frozenset(payload.model_fields_set)
    )


async def delete_contact(
    contact_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteContactHandlerDep,
) -> Response:
    """Физически удаляет контакт в tenant текущего участника."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(DeleteContactCommand(ContactIdVO.from_value(contact_id)))
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)
