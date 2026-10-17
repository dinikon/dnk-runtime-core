from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.crm.application.contact.command.create_contact.command import (
    CreateContactCommand,
)
from src.modules.crm.domain.contact.error import InvalidContactNameError
from src.modules.crm.presentation.contact.depends import CreateContactHandlerDep
from src.modules.crm.presentation.contact.http.request.create_contact import (
    CreateContactRequest,
)
from src.modules.crm.presentation.contact.http.response.create_contact import (
    CreateContactResponse,
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
