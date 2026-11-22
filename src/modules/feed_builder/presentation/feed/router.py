from fastapi import APIRouter, Depends
from src.modules.feed_builder.presentation.feed.http.controller.create_feed import (
    create_feed,
)
from src.modules.feed_builder.presentation.feed.http.controller.patch_feed import (
    patch_feed,
)
from src.modules.feed_builder.presentation.feed.http.controller.delete_feed import (
    delete_feed,
)
from src.modules.feed_builder.presentation.feed.http.controller.get_feed import get_feed
from src.modules.feed_builder.presentation.feed.http.controller.list_feeds import (
    list_feeds,
)
from src.modules.feed_builder.presentation.feed.http.response.create_feed import (
    CreateFeedResponse,
)
from src.modules.feed_builder.presentation.feed.http.response.patch_feed import (
    PatchFeedResponse,
)
from src.modules.feed_builder.presentation.feed.http.response.get_feed import (
    GetFeedResponse,
)
from src.modules.feed_builder.presentation.feed.http.response.list_feeds import (
    ListFeedsResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.feed_builder.presentation.feed.http.controller.get_feed_schema import (
    get_feed_schema,
)
from src.modules.feed_builder.presentation.feed.http.controller.put_feed_schema import (
    put_feed_schema,
)
from src.modules.feed_builder.presentation.feed.http.response.get_feed_schema import (
    GetFeedSchemaResponse,
)
from src.modules.feed_builder.presentation.feed.http.response.put_feed_schema import (
    PutFeedSchemaResponse,
)
from src.modules.feed_builder.presentation.feed.http.schema.body_limit import (
    SchemaBodyLimitRoute,
)
from src.modules.feed_builder.presentation.feed.http.controller.list_field_types import (
    list_field_types,
)
from src.modules.feed_builder.presentation.feed.http.controller.list_source_paths import (
    list_source_paths,
)
from src.modules.feed_builder.presentation.feed.http.controller.list_transforms import (
    list_transforms,
)
from src.modules.feed_builder.presentation.feed.http.response.list_field_types import (
    ListFieldTypesResponse,
)
from src.modules.feed_builder.presentation.feed.http.response.list_source_paths import (
    ListSourcePathsResponse,
)
from src.modules.feed_builder.presentation.feed.http.response.list_transforms import (
    ListTransformsResponse,
)
from src.modules.feed_builder.presentation.feed.http.controller.preview_field_calculation import (
    preview_field_calculation,
)
from src.modules.feed_builder.presentation.feed.http.response.preview_field_calculation import (
    PreviewFieldCalculationResponse,
)
from src.modules.feed_builder.presentation.feed.http.controller.list_calculation_parameters import (
    list_calculation_parameters,
)
from src.modules.feed_builder.presentation.feed.http.response.list_calculation_parameters import (
    ListCalculationParametersResponse,
)
from src.modules.feed_builder.presentation.feed.http.controller.list_calculation_operations import (
    list_calculation_operations,
)
from src.modules.feed_builder.presentation.feed.http.response.list_calculation_operations import (
    ListCalculationOperationsResponse,
)

from src.modules.feed_builder.presentation.feed.export_depends import (
    prepare_export_transaction,
    require_catalog_export_access,
)
from src.modules.feed_builder.presentation.feed.http.controller.preview_feed import (
    preview_feed,
)
from src.modules.feed_builder.presentation.feed.http.controller.download_test_csv import (
    download_test_csv,
)
from src.modules.feed_builder.presentation.feed.http.response.preview_feed import (
    PreviewFeedResponse,
)

router = APIRouter(prefix="/feed-builder/feeds", tags=["feed-builder"])

router.add_api_route(
    "",
    list_feeds,
    methods=["GET"],
    response_model=ListFeedsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{feed_id}",
    get_feed,
    methods=["GET"],
    response_model=GetFeedResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_feed,
    methods=["POST"],
    status_code=201,
    response_model=CreateFeedResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{feed_id}",
    patch_feed,
    methods=["PATCH"],
    response_model=PatchFeedResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{feed_id}",
    delete_feed,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)


schema_router = APIRouter(route_class=SchemaBodyLimitRoute)
schema_router.add_api_route(
    "/{feed_id}/schema",
    get_feed_schema,
    methods=["GET"],
    response_model=GetFeedSchemaResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(require_authenticated_request_context)],
)
schema_router.add_api_route(
    "/{feed_id}/schema/draft",
    put_feed_schema,
    methods=["PUT"],
    response_model=PutFeedSchemaResponse,
    response_model_exclude_unset=True,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.include_router(schema_router)


metadata_router = APIRouter(prefix="/feed-builder", tags=["feed-builder"])
metadata_router.add_api_route(
    "/field-types",
    list_field_types,
    methods=["GET"],
    response_model=ListFieldTypesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
metadata_router.add_api_route(
    "/source-paths",
    list_source_paths,
    methods=["GET"],
    response_model=ListSourcePathsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
metadata_router.add_api_route(
    "/transforms",
    list_transforms,
    methods=["GET"],
    response_model=ListTransformsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)


preview_router = APIRouter(route_class=SchemaBodyLimitRoute)
preview_router.add_api_route(
    "/{feed_id}/calculation-preview",
    preview_field_calculation,
    methods=["POST"],
    response_model=PreviewFieldCalculationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
preview_router.add_api_route(
    "/{feed_id}/preview",
    preview_feed,
    methods=["POST"],
    response_model=PreviewFeedResponse,
    dependencies=[
        Depends(prepare_export_transaction),
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
        Depends(require_catalog_export_access),
    ],
)
preview_router.add_api_route(
    "/{feed_id}/test-csv",
    download_test_csv,
    methods=["POST"],
    responses={
        200: {
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}
        }
    },
    dependencies=[
        Depends(prepare_export_transaction),
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
        Depends(require_catalog_export_access),
    ],
)
router.include_router(preview_router)
metadata_router.add_api_route(
    "/calculation-parameters",
    list_calculation_parameters,
    methods=["GET"],
    response_model=ListCalculationParametersResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
metadata_router.add_api_route(
    "/calculation-operations",
    list_calculation_operations,
    methods=["GET"],
    response_model=ListCalculationOperationsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
