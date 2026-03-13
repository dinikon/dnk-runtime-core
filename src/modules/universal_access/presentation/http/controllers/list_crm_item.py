from uuid import uuid4

from fastapi import APIRouter

from src.modules.universal_access.presentation.http.requests.list_crm_item import (
    ListCrmItemRequestSchema,
)
from src.modules.universal_access.presentation.http.responses.list_crm_item import (
    ListCrmItemEntryResponseSchema,
    ListCrmItemResponseSchema,
)

router = APIRouter(tags=["crm.item"])


@router.post("/crm.item.list")
def crm_list_item(
    request: ListCrmItemRequestSchema,
) -> ListCrmItemResponseSchema:
    return ListCrmItemResponseSchema(
        items=[
            ListCrmItemEntryResponseSchema(
                item_id=uuid4(),
                fields={"objectId": str(request.objectId)},
            )
        ],
        page=request.page,
        page_size=request.page_size,
    )
