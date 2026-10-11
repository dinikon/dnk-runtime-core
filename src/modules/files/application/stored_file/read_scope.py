from uuid import UUID
from src.modules.files.domain.error import (
    StorageNotFoundError,
    InvalidStorageStateError,
)
from src.modules.files.application.stored_file.error import InvalidFileQueryError
from src.modules.files.application.stored_file.file_category import FileCategory
from src.modules.files.application.stored_file.port.query_repository import (
    StoredFileQueryRepositoryProtocol,
)


def validate_bucket_ids(bucket_ids: tuple[UUID, ...]) -> None:
    """Проверяет ограниченный список UUID дисков для чтения."""
    if len(bucket_ids) > 50 or any(
        not isinstance(identifier, UUID) for identifier in bucket_ids
    ):
        raise InvalidFileQueryError("Invalid bucket filter.")


def validate_file_list_parameters(
    search: str,
    bucket_ids: tuple[UUID, ...],
    category: FileCategory | None,
    page: int,
    page_size: int,
) -> None:
    """Проверяет параметры проекций вне HTTP и без post_init у Query."""
    validate_bucket_ids(bucket_ids)
    if not isinstance(search, str) or len(search.strip()) > 255:
        raise InvalidFileQueryError("Search is too long.")
    if category is not None and category not in FileCategory:
        raise InvalidFileQueryError("Invalid file category.")
    if (
        type(page) is not int
        or page < 1
        or type(page_size) is not int
        or page_size not in {10, 20, 50, 100}
    ):
        raise InvalidFileQueryError("Invalid file pagination.")


async def ensure_selected_buckets(
    repository: StoredFileQueryRepositoryProtocol, bucket_ids: tuple[UUID, ...]
) -> None:
    """Проверяет доступность явного фильтра; чужой и отсутствующий ID не различаются."""
    if not bucket_ids:
        return
    buckets = await repository.selected_buckets(bucket_ids)
    if {item.bucket_id for item in buckets} != set(bucket_ids):
        raise StorageNotFoundError("Selected storage was not found.")
    if any(item.status != "ready" for item in buckets):
        raise InvalidStorageStateError("Selected storage is not ready.")
