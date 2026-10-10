from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.files.presentation.bucket.http.controller.list_buckets import (
    list_buckets,
)
from src.modules.files.presentation.bucket.http.response.list_buckets import (
    ListBucketsItemResponse,
)

router = APIRouter(tags=["Files"])
router.add_api_route(
    "/files/buckets/",
    list_buckets,
    methods=["GET"],
    response_model=list[ListBucketsItemResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
