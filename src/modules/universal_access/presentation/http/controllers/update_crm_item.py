from fastapi import APIRouter

from src.modules.universal_access.presentation.http.requests.update_crm_item import (
    UpdateCrmItemRequestSchema,
)
from src.modules.universal_access.presentation.http.responses.update_crm_item import (
    UpdateCrmItemResponseSchema,
)

router = APIRouter(tags=["crm.item"])


@router.post("/universal-access/crm.item.update")
def crm_update_item(
    request: UpdateCrmItemRequestSchema,
) -> UpdateCrmItemResponseSchema:
    return UpdateCrmItemResponseSchema(
        item_id=request.itemId,
        result=request.fields,
    )
