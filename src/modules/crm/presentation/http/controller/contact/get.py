from datetime import datetime

from fastapi import APIRouter

from src.modules.crm.presentation.http.requests.contact.get import (
    GetContactRequestSchema,
)
from src.modules.crm.presentation.http.responses.contact.get import (
    GetContactResponseSchema,
)

router = APIRouter(tags=["crm.contact"])


@router.post("/crm/contact/get", response_model=GetContactResponseSchema)
async def get_contact(
    payload: GetContactRequestSchema,
) -> GetContactResponseSchema:
    timestamp = datetime.now()
    return GetContactResponseSchema(
        id=payload.contact_id,
        created_at=timestamp,
        updated_at=timestamp,
        first_name="John",
        last_name="Doe",
        middle_name=None,
    )
