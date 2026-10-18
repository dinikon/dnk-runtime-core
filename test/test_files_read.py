"""Контракты чтения Files вне HTTP: классификация и допустимые фильтры."""

import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.modules.files.application.stored_file.file_category import (
    FileCategory,
    DOCUMENT_MIME_TYPES,
    classify_file,
)
from src.modules.files.application.stored_file.error import InvalidFileQueryError
from src.modules.files.application.stored_file.port.query_repository import (
    FileReadBucketDTO,
    StoredFileQueryRepositoryProtocol,
)
from src.modules.files.application.stored_file.query.list_files.query import (
    ListFilesQuery,
)
from src.modules.files.application.stored_file.query.list_files.handler import (
    ListFilesHandler,
)
from src.modules.files.application.stored_file.query.list_files.dto import (
    ListFilesResultDTO,
)
from src.modules.files.application.stored_file.query.list_trashed_files.query import (
    ListTrashedFilesQuery,
)
from src.modules.files.application.stored_file.query.list_trashed_files.handler import (
    ListTrashedFilesHandler,
)
from src.modules.files.application.stored_file.query.list_trashed_files.dto import (
    ListTrashedFilesResultDTO,
)
from src.modules.files.application.stored_file.query.get_files_overview.query import (
    GetFilesOverviewQuery,
)
from src.modules.files.application.stored_file.query.get_files_overview.handler import (
    GetFilesOverviewHandler,
)
from src.modules.files.application.stored_file.query.get_files_overview.dto import (
    GetFilesOverviewResultDTO,
)
from src.modules.files.domain.error import (
    StorageNotFoundError,
    InvalidStorageStateError,
)


class FilesReadContractTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет Application-контракты без ORM, MinIO и HTTP-типов."""

    def setUp(self) -> None:
        """Создаёт порт проекций и доверенный tenant."""
        self.tenant = uuid4()
        self.bucket = uuid4()
        self.repository = AsyncMock(spec=StoredFileQueryRepositoryProtocol)
        self.repository.selected_buckets.return_value = (
            FileReadBucketDTO(self.bucket, "ready"),
        )

    def test_category_normalizes_mime_and_limits_document_set(self) -> None:
        """Классификация не зависит от регистра/параметров и не считает audio документом."""
        for mime in DOCUMENT_MIME_TYPES:
            with self.subTest(mime=mime):
                self.assertEqual(
                    classify_file(f"  {mime.upper()} ; charset=UTF-8"),
                    FileCategory.DOCUMENTS,
                )
        for mime, category in (
            (" IMAGE/PNG; foo=bar ", FileCategory.IMAGES),
            ("video/MP4", FileCategory.VIDEOS),
            ("audio/mpeg", FileCategory.OTHER),
            ("application/zip", FileCategory.OTHER),
            ("application/octet-stream", FileCategory.OTHER),
            ("text/unknown", FileCategory.OTHER),
        ):
            with self.subTest(mime=mime):
                self.assertEqual(classify_file(mime), category)

    async def test_list_handlers_normalize_and_return_specific_dtos(self) -> None:
        """Trim и повторяющиеся диски нормализуются; результаты сценариев не объединяются."""
        self.repository.list_files.return_value = ListFilesResultDTO((), 0, 1, 20)
        self.repository.list_trashed_files.return_value = ListTrashedFilesResultDTO(
            (), 0, 1, 20
        )
        for handler, query, method, result_type in (
            (ListFilesHandler, ListFilesQuery, "list_files", ListFilesResultDTO),
            (
                ListTrashedFilesHandler,
                ListTrashedFilesQuery,
                "list_trashed_files",
                ListTrashedFilesResultDTO,
            ),
        ):
            result = await handler(self.repository).execute(
                query(
                    self.tenant,
                    search="  Звіт  ",
                    bucket_ids=(self.bucket, self.bucket),
                )
            )
            self.assertIsInstance(result, result_type)
            called = getattr(self.repository, method).await_args.args[0]
            self.assertEqual(called.search, "Звіт")
            self.assertEqual(called.bucket_ids, (self.bucket,))

    async def test_invalid_queries_never_reach_read_repository(self) -> None:
        """Внутренний caller подчиняется тем же пределам, что HTTP."""
        for handler_type, query_type in (
            (ListFilesHandler, ListFilesQuery),
            (ListTrashedFilesHandler, ListTrashedFilesQuery),
        ):
            for fields in (
                {"search": "x" * 256},
                {"page": 0},
                {"page": True},
                {"page_size": 30},
                {"page_size": True},
                {"category": "unknown"},
                {"bucket_ids": (self.bucket,) * 51},
            ):
                with (
                    self.subTest(handler=handler_type, fields=fields),
                    self.assertRaises(InvalidFileQueryError),
                ):
                    await handler_type(self.repository).execute(
                        query_type(self.tenant, **fields)
                    )
        self.repository.selected_buckets.assert_not_awaited()
        self.repository.list_files.assert_not_awaited()
        self.repository.list_trashed_files.assert_not_awaited()

    async def test_unknown_bucket_precedes_not_ready_and_all_disks_need_no_lookup(
        self,
    ) -> None:
        """Чужой ID не отличается от отсутствующего; ready проверяется после существования."""
        self.repository.selected_buckets.return_value = (
            FileReadBucketDTO(self.bucket, "preparing"),
        )
        handler = ListFilesHandler(self.repository)
        with self.assertRaises(StorageNotFoundError):
            await handler.execute(
                ListFilesQuery(self.tenant, bucket_ids=(self.bucket, uuid4()))
            )
        with self.assertRaises(InvalidStorageStateError):
            await handler.execute(
                ListFilesQuery(self.tenant, bucket_ids=(self.bucket,))
            )
        self.repository.selected_buckets.reset_mock()
        await handler.execute(ListFilesQuery(self.tenant))
        self.repository.selected_buckets.assert_not_awaited()

    async def test_overview_has_only_bucket_scope(self) -> None:
        """Сводка нормализует выбранные диски и возвращает свой контракт."""
        self.repository.get_files_overview.return_value = GetFilesOverviewResultDTO(
            0, 0, 0, 0, 0, 0, ()
        )
        result = await GetFilesOverviewHandler(self.repository).execute(
            GetFilesOverviewQuery(
                self.tenant,
                bucket_ids=(self.bucket, self.bucket),
            )
        )
        self.assertIsInstance(result, GetFilesOverviewResultDTO)
        self.assertEqual(
            self.repository.get_files_overview.await_args.args[0].bucket_ids,
            (self.bucket,),
        )
        with self.assertRaises(InvalidFileQueryError):
            await GetFilesOverviewHandler(self.repository).execute(
                GetFilesOverviewQuery(self.tenant, (self.bucket,) * 51)
            )
