"""Проверки использования перед всеми путями удаления Files."""

from datetime import UTC, datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.files.application.stored_file.command.trash_file.command import (
    TrashFileCommand,
)
from src.modules.files.application.stored_file.command.trash_file.handler import (
    TrashFileHandler,
)
from src.modules.files.application.stored_file.command.request_file_purge.command import (
    RequestFilePurgeCommand,
)
from src.modules.files.application.stored_file.command.request_file_purge.handler import (
    RequestFilePurgeHandler,
)
from src.modules.files.application.stored_file.command.purge_file.command import (
    PurgeFileCommand,
)
from src.modules.files.application.stored_file.command.purge_file.handler import (
    PurgeFileHandler,
)
from src.modules.files.application.stored_file.command.empty_trash.command import (
    EmptyTrashCommand,
)
from src.modules.files.application.stored_file.command.empty_trash.handler import (
    EmptyTrashHandler,
)
from src.modules.files.application.stored_file.command.empty_trash.dto import (
    EmptyTrashCandidateDTO,
)
from src.modules.files.application.stored_file.command.cleanup_expired_trash.command import (
    CleanupExpiredTrashCommand,
)
from src.modules.files.application.stored_file.command.cleanup_expired_trash.handler import (
    CleanupExpiredTrashHandler,
)
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.stored_file.error import FileInUseError
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FilesUsageTests(IsolatedAsyncioTestCase):
    """Факт использования проверяется под lock до мутации, очереди и физического удаления."""

    def setUp(self) -> None:
        """Создаёт ready-файл и явно используемый ресурс."""
        self.now, self.tenant, self.actor = datetime.now(UTC), uuid4(), uuid4()
        self.file = StoredFile.create(
            file_id=EntityIdVO(uuid4()),
            bucket_id=EntityIdVO(uuid4()),
            name=FileNameVO("image.png"),
            content_type="image/png",
            size=FileSizeVO(1),
            created_at=self.now - timedelta(days=60),
        )
        self.file.mark_uploaded(1)
        self.files, self.usage, self.queries, self.queue = (
            Mock(),
            Mock(),
            Mock(),
            Mock(),
        )
        self.files.get_for_update = AsyncMock(return_value=self.file)
        self.files.save, self.files.remove = AsyncMock(), AsyncMock()
        self.usage.used = AsyncMock(return_value=(self.file.id.uuid,))
        self.queue.schedule = AsyncMock()
        self.clock, self.uuids = Mock(), Mock()
        self.clock.now.return_value = self.now
        self.uuids.new.side_effect = uuid4

    async def test_trash_and_explicit_purge_reject_live_references_before_mutation(
        self,
    ) -> None:
        """Одиночные команды не оставляют изменённый агрегат или job."""
        with self.assertRaises(FileInUseError):
            await TrashFileHandler(self.files, self.clock, self.usage).execute(
                TrashFileCommand(self.tenant, self.file.id.uuid, self.actor)
            )
        self.assertEqual(self.file.status, StoredFileStatus.READY)
        self.files.save.assert_not_awaited()
        self.file.move_to_trash(EntityIdVO(self.actor), self.now - timedelta(days=31))
        with self.assertRaises(FileInUseError):
            await RequestFilePurgeHandler(
                self.files, self.queue, self.clock, self.uuids, self.usage
            ).execute(
                RequestFilePurgeCommand(self.tenant, self.file.id.uuid, self.actor)
            )
        self.assertEqual(self.file.status, StoredFileStatus.TRASHED)
        self.queue.schedule.assert_not_awaited()

    async def test_empty_and_expired_cleanup_skip_used_candidates_without_losing_cursor(
        self,
    ) -> None:
        """Один используемый файл не отменяет пакет и не запускает purge."""
        self.file.move_to_trash(EntityIdVO(self.actor), self.now - timedelta(days=31))
        candidate = EmptyTrashCandidateDTO(self.file.id.uuid)
        self.queries.empty_trash_candidates = AsyncMock(return_value=(candidate,))
        self.queries.cleanup_candidates = AsyncMock(return_value=(candidate,))
        self.queue.terminal_or_missing = AsyncMock(return_value=set())
        empty = await EmptyTrashHandler(
            self.files, self.queries, self.queue, self.clock, self.uuids, self.usage
        ).execute(EmptyTrashCommand(self.tenant, self.now, batch_size=1))
        self.assertEqual(
            (empty.queued_count, empty.next_after_id), (0, self.file.id.uuid)
        )
        expired = await CleanupExpiredTrashHandler(
            self.files, self.queries, self.queue, self.uuids, self.usage
        ).execute(CleanupExpiredTrashCommand(self.tenant, self.now, batch_size=1))
        self.assertEqual(expired.queued_count, 0)
        self.queue.schedule.assert_not_awaited()
        self.assertEqual(self.file.status, StoredFileStatus.TRASHED)

    async def test_final_purge_rechecks_usage_before_any_storage_io(self) -> None:
        """Защищает также старые purging-записи и уже поставленные задания."""
        self.file.move_to_trash(EntityIdVO(self.actor), self.now - timedelta(days=31))
        operation = EntityIdVO(uuid4())
        self.file.request_purge(self.now, operation)
        buckets, providers, storage = Mock(), Mock(), Mock()
        handler = PurgeFileHandler(self.files, buckets, providers, storage, self.usage)
        with self.assertRaises(FileInUseError):
            await handler.execute(
                PurgeFileCommand(self.tenant, self.file.id.uuid, operation.uuid)
            )
        storage.resolve.assert_not_called()
        self.files.remove.assert_not_awaited()
