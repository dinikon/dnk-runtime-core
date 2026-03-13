from uuid import uuid4

from fastapi import APIRouter

from src.modules.universal_access.presentation.http.requests.add_crm_item import (
    AddCrmItemRequestSchema,
)
from src.modules.universal_access.presentation.http.responses.add_crm_item import (
    AddCrmItemResponseSchema,
)

router = APIRouter(tags=["crm.item"])


@router.post("/crm.item.add")
def crm_add_item(
    request: AddCrmItemRequestSchema,
) -> AddCrmItemResponseSchema:
    return AddCrmItemResponseSchema(
        item_id=uuid4(),
        result=request.fields,
    )
