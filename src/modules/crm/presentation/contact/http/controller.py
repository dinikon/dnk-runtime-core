from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.crm.application.contact.command.create_contact.command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.query.get_contact.query import GetContactQuery
from src.modules.crm.domain.contact.error import (
    ContactNotFoundError,
    InvalidContactNameError,
)
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.presentation.contact.depends import (
    CreateContactHandlerDep,
    GetContactHandlerDep,
)
from src.modules.crm.presentation.contact.http.request import CreateContactRequest
from src.modules.crm.presentation.contact.http.response import (
    CreateContactResponse,
    GetContactResponse,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.uuid.depends import UuidDep


async def create_contact(
    payload: CreateContactRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateContactHandlerDep,
    uuid_generator: UuidDep,
) -> CreateContactResponse:
    """Создаёт контакт в tenant аутентифицированного участника."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    command = CreateContactCommand(
        tenant_id=EntityIdVO.from_value(principal.tenant_id),
        actor_id=EntityIdVO.from_value(principal.user_id),
        contact_id=ContactIdVO.from_value(uuid_generator.new()),
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
        tenant_id=EntityIdVO.from_value(principal.tenant_id),
        contact_id=ContactIdVO.from_value(contact_id),
    )
    try:
        result = await handler.execute(query)
    except ContactNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetContactResponse.from_dto(result)
