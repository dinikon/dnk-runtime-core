from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter

from src.modules.crm.presentation.http.requests.contact.list import (
    ListContactsRequestSchema,
)
from src.modules.crm.presentation.http.responses.contact.list import (
    ContactListItemResponseSchema,
    ListContactsResponseSchema,
)

router = APIRouter(tags=["crm.contact"])


@router.post("/contact/list", response_model=ListContactsResponseSchema)
async def list_contacts(
    payload: ListContactsRequestSchema,
) -> ListContactsResponseSchema:
    timestamp = datetime.now()
    return ListContactsResponseSchema(
        items=[
            ContactListItemResponseSchema(
                id=uuid4(),
                created_at=timestamp,
                updated_at=timestamp,
                first_name=payload.first_name or "John",
                last_name=payload.last_name or "Doe",
                middle_name=payload.middle_name,
            )
        ],
        total=1,
        limit=payload.limit,
        offset=payload.offset,
    )
