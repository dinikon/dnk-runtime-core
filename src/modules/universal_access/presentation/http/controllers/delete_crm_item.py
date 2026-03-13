from fastapi import APIRouter

from src.modules.universal_access.presentation.http.requests.delete_crm_item import (
    DeleteCrmItemRequestSchema,
)
from src.modules.universal_access.presentation.http.responses.delete_crm_item import (
    DeleteCrmItemResponseSchema,
)

router = APIRouter(tags=["crm.item"])


@router.post("/crm.item.delete")
def crm_delete_item(
    request: DeleteCrmItemRequestSchema,
) -> DeleteCrmItemResponseSchema:
    return DeleteCrmItemResponseSchema(
        item_id=request.itemId,
        ok=True,
    )
