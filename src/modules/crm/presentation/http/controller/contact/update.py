from datetime import datetime

from fastapi import APIRouter

from src.modules.crm.presentation.http.requests.contact.update import (
    UpdateContactRequestSchema,
)
from src.modules.crm.presentation.http.responses.contact.update import (
    UpdateContactResponseSchema,
)

router = APIRouter(tags=["crm.contact"])


@router.post("/crm/contact/update", response_model=UpdateContactResponseSchema)
async def update_contact(
    payload: UpdateContactRequestSchema,
) -> UpdateContactResponseSchema:
    timestamp = datetime.now()
    return UpdateContactResponseSchema(
        id=payload.contact_id,
        created_at=timestamp,
        updated_at=timestamp,
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
    )
