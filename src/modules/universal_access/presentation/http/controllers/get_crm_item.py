from fastapi import APIRouter

from src.modules.universal_access.presentation.http.requests.get_crm_item import (
    GetCrmItemRequestSchema,
)
from src.modules.universal_access.presentation.http.responses.get_crm_item import (
    GetCrmItemResponseSchema,
)

router = APIRouter(tags=["crm.item"])


@router.post("/crm.item.get")
def crm_get_item(
    request: GetCrmItemRequestSchema,
) -> GetCrmItemResponseSchema:
    return GetCrmItemResponseSchema(result={"status": "success"})
