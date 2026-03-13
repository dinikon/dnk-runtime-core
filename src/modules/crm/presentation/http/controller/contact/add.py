from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter

from src.modules.crm.presentation.http.requests.contact.add import (
    AddContactRequestSchema,
)
from src.modules.crm.presentation.http.responses.contact.add import (
    AddContactResponseSchema,
)
from src.modules.shared.depends.authentication import (
    AuthenticatedRequestContextDep,
)

router = APIRouter(tags=["crm.contact"])


@router.post("/contact/add", response_model=AddContactResponseSchema)
async def add_contact(
    payload: AddContactRequestSchema,
    request_context: AuthenticatedRequestContextDep,
) -> AddContactResponseSchema:
    print(request_context)
    timestamp = datetime.now()
    return AddContactResponseSchema(
        id=uuid4(),
        created_at=timestamp,
        updated_at=timestamp,
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
    )
