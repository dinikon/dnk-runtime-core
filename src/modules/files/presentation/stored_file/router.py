from fastapi import APIRouter, Depends
from src.modules.files.presentation.depends.admin import require_files_admin_context
from src.modules.files.presentation.stored_file.http.controller.list_files import (
    list_files,
)
from src.modules.files.presentation.stored_file.http.response.list_files import (
    ListFilesResponse,
)
from src.modules.files.presentation.stored_file.http.controller.list_trashed_files import (
    list_trashed_files,
)
from src.modules.files.presentation.stored_file.http.response.list_trashed_files import (
    ListTrashedFilesResponse,
)
from src.modules.files.presentation.stored_file.http.controller.get_files_overview import (
    get_files_overview,
)
from src.modules.files.presentation.stored_file.http.response.get_files_overview import (
    GetFilesOverviewResponse,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.files.presentation.stored_file.http.controller.upload_file import (
    upload_file,
)
from src.modules.files.presentation.depends.admin import require_files_upload_context
from src.modules.files.presentation.stored_file.http.response.upload_file import (
    UploadFileResponse,
)
from src.modules.files.presentation.stored_file.http.request.upload_file import (
    UploadFileRequest,
)
from src.modules.files.presentation.stored_file.http.controller.trash_file import (
    trash_file,
)
from src.modules.files.presentation.depends.admin import require_files_trash_context
from src.modules.files.presentation.stored_file.http.response.trash_file import (
    TrashFileResponse,
)
from src.modules.files.presentation.stored_file.http.controller.restore_file import (
    restore_file,
)
from src.modules.files.presentation.depends.admin import require_files_restore_context
from src.modules.files.presentation.stored_file.http.response.restore_file import (
    RestoreFileResponse,
)
from src.modules.files.presentation.stored_file.http.controller.request_file_purge import (
    request_file_purge,
)
from src.modules.files.presentation.depends.admin import require_files_purge_context
from fastapi import Response
from src.modules.files.presentation.depends.admin import require_files_preview_context
from src.modules.files.presentation.stored_file.http.controller.get_file_preview import (
    get_file_preview,
)
from src.modules.files.presentation.stored_file.http.response.get_file_preview import (
    GetFilePreviewResponse,
)

from src.modules.files.presentation.stored_file.http.controller.request_trash_empty import (
    request_trash_empty,
)
from src.modules.files.presentation.stored_file.http.response.request_trash_empty import (
    RequestTrashEmptyResponse,
)
from src.modules.files.presentation.depends.admin import (
    require_files_empty_trash_context,
)

router = APIRouter(tags=["Files"])
router.add_api_route(
    "/files/trash/",
    request_trash_empty,
    methods=["DELETE"],
    status_code=202,
    response_model=RequestTrashEmptyResponse,
    dependencies=[Depends(require_files_empty_trash_context), Depends(require_csrf)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Tenant admin and global files.purge permission required"},
    },
)
router.add_api_route(
    "/files/items/",
    list_files,
    methods=["GET"],
    response_model=ListFilesResponse,
    dependencies=[Depends(require_files_admin_context)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Tenant admin required"},
        404: {"description": "Selected storage not found"},
        409: {"description": "Selected storage not ready"},
    },
)
router.add_api_route(
    "/files/trash/",
    list_trashed_files,
    methods=["GET"],
    response_model=ListTrashedFilesResponse,
    dependencies=[Depends(require_files_admin_context)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Tenant admin required"},
        404: {"description": "Selected storage not found"},
        409: {"description": "Selected storage not ready"},
    },
)
router.add_api_route(
    "/files/overview/",
    get_files_overview,
    methods=["GET"],
    response_model=GetFilesOverviewResponse,
    dependencies=[Depends(require_files_admin_context)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Tenant admin required"},
        404: {"description": "Selected storage not found"},
        409: {"description": "Selected storage not ready"},
    },
)


router.add_api_route(
    "/files/items/",
    upload_file,
    methods=["POST"],
    status_code=201,
    response_model=UploadFileResponse,
    dependencies=[Depends(require_files_upload_context), Depends(require_csrf)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Admin, authorization or CSRF denied"},
        404: {"description": "File or storage not found"},
        409: {"description": "File or storage state conflict"},
        422: {"description": "Invalid fields"},
        503: {"description": "Storage unavailable"},
        413: {"description": "Console upload limit exceeded"},
        408: {"description": "Console upload reception timed out"},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {"schema": UploadFileRequest.model_json_schema()}
            },
        }
    },
)

router.add_api_route(
    "/files/items/{file_id}/",
    trash_file,
    methods=["DELETE"],
    status_code=200,
    response_model=TrashFileResponse,
    dependencies=[Depends(require_files_trash_context), Depends(require_csrf)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Admin, authorization or CSRF denied"},
        404: {"description": "File or storage not found"},
        409: {"description": "File or storage state conflict"},
        422: {"description": "Invalid fields"},
        503: {"description": "Storage unavailable"},
    },
)

router.add_api_route(
    "/files/items/{file_id}/restore/",
    restore_file,
    methods=["POST"],
    status_code=200,
    response_model=RestoreFileResponse,
    dependencies=[Depends(require_files_restore_context), Depends(require_csrf)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Admin, authorization or CSRF denied"},
        404: {"description": "File or storage not found"},
        409: {"description": "File or storage state conflict"},
        422: {"description": "Invalid fields"},
        503: {"description": "Storage unavailable"},
    },
)

router.add_api_route(
    "/files/trash/{file_id}/",
    request_file_purge,
    methods=["DELETE"],
    status_code=202,
    response_class=Response,
    response_model=None,
    dependencies=[Depends(require_files_purge_context), Depends(require_csrf)],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Admin, authorization or CSRF denied"},
        404: {"description": "File or storage not found"},
        409: {"description": "File or storage state conflict"},
        422: {"description": "Invalid fields"},
        503: {"description": "Storage unavailable"},
    },
)

router.add_api_route(
    "/files/items/{file_id}/preview/",
    get_file_preview,
    methods=["GET"],
    status_code=200,
    response_class=GetFilePreviewResponse,
    response_model=None,
    dependencies=[Depends(require_files_preview_context)],
    responses={
        200: {
            "description": "Inline browser preview of a ready file; text is served as text/plain",
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
        401: {"description": "Unauthorized"},
        403: {"description": "Tenant admin or file read permission required"},
        404: {"description": "Ready file or owned object not found"},
        409: {"description": "Storage ownership conflict"},
        415: {"description": "File format does not support preview"},
        503: {"description": "Storage unavailable"},
    },
)
