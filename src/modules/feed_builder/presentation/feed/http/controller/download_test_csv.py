from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationDependencyUnavailableError,
)
from src.modules.feed_builder.application.feed.query.download_test_csv.query import (
    DownloadTestCsvQuery,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedNotFoundError,
    FeedVersionConflictError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.feed_builder.presentation.feed.export_depends import (
    DownloadTestCsvHandlerDep,
)
from src.modules.feed_builder.presentation.feed.http.request.download_test_csv import (
    DownloadTestCsvRequest,
)
from src.modules.feed_builder.presentation.feed.http.response.download_test_csv import (
    DownloadTestCsvErrorResponse,
    TestCsvIssueResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def download_test_csv(
    feed_id: UUID,
    payload: DownloadTestCsvRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: DownloadTestCsvHandlerDep,
) -> StreamingResponse:
    """Отдаёт завершённый CSV либо диагностику блокирующих ошибок."""
    for action in (
        "feed_builder.feed.read",
        "feed_builder.publication.read",
        "feed_builder.feed.calculation_preview",
    ):
        await require_feed_access(
            context, authorization, action=action, feed_id=feed_id
        )
    try:
        result = await handler.execute(
            DownloadTestCsvQuery(FeedIdVO(feed_id), payload.expected_version)
        )
    except FeedNotFoundError as exc:
        raise HTTPException(
            404, {"code": "FEED_NOT_FOUND", "message": str(exc)}
        ) from exc
    except (FeedArchivedError, FeedVersionConflictError) as exc:
        raise HTTPException(
            409, {"code": "FEED_CONFLICT", "message": str(exc)}
        ) from exc
    except InvalidFeedValueError as exc:
        raise HTTPException(
            422, {"code": "TEST_CSV_INVALID", "message": str(exc)}
        ) from exc
    except CalculationDependencyUnavailableError as exc:
        raise HTTPException(
            503, {"code": "DEPENDENCY_UNAVAILABLE", "message": str(exc)}
        ) from exc
    if result.file is None:
        detail = DownloadTestCsvErrorResponse(
            code="TEST_CSV_BLOCKED",
            message="Исправьте ошибки публикаций перед скачиванием.",
            issues=tuple(
                TestCsvIssueResponse.model_validate(issue) for issue in result.issues
            ),
        )
        raise HTTPException(422, detail.model_dump(mode="json"))
    return StreamingResponse(
        result.file.chunks(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Cache-Control": "no-store",
        },
        background=BackgroundTask(result.file.close),
    )
