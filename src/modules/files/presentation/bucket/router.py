from fastapi import APIRouter, Depends
from src.modules.files.presentation.depends.admin import require_files_admin_context
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
    dependencies=[Depends(require_files_admin_context)],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}},
)
