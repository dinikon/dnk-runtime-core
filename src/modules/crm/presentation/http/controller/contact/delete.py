from fastapi import APIRouter

from src.modules.crm.presentation.http.requests.contact.delete import (
    DeleteContactRequestSchema,
)
from src.modules.crm.presentation.http.responses.contact.delete import (
    DeleteContactResponseSchema,
)

router = APIRouter(tags=["crm.contact"])


@router.post("/crm/contact/delete", response_model=DeleteContactResponseSchema)
async def delete_contact(
    payload: DeleteContactRequestSchema,
) -> DeleteContactResponseSchema:
    return DeleteContactResponseSchema(
        id=payload.contact_id,
        ok=True,
    )
