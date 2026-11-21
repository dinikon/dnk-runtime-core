"""Контракты ручной очистки корзины и повторная проверка кандидатов."""

from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from src.modules.files.application.stored_file.command.empty_trash.command import (
    EmptyTrashCommand,
)
from src.modules.files.application.stored_file.command.empty_trash.dto import (
    EmptyTrashCandidateDTO,
)
from src.modules.files.application.stored_file.command.empty_trash.handler import (
    EmptyTrashHandler,
)
from src.modules.files.application.stored_file.command.request_trash_empty.command import (
    RequestTrashEmptyCommand,
)
from src.modules.files.application.stored_file.command.request_trash_empty.handler import (
    RequestTrashEmptyHandler,
)
from src.modules.files.application.stored_file.port.query_repository import (
    StoredFileQueryRepositoryProtocol,
)
from src.modules.files.application.stored_file.port.purge_queue import (
    FilePurgeQueueProtocol,
)
from src.modules.files.domain.stored_file.repository import StoredFileRepositoryProtocol
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class EmptyTrashTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет сценарии без базы и MinIO, используя реальные доменные переходы."""

    def setUp(self) -> None:
        """Собирает порты и управляемые часы для всех переходов."""
        self.now = datetime(2026, 10, 11, tzinfo=UTC)
        self.cutoff = self.now - timedelta(seconds=1)
        self.tenant = uuid4()
        self.files = AsyncMock(spec=StoredFileRepositoryProtocol)
        self.queries = AsyncMock(spec=StoredFileQueryRepositoryProtocol)
        self.queue = AsyncMock(spec=FilePurgeQueueProtocol)
        self.clock = Mock()
        self.clock.now.return_value = self.now
        self.uuids = Mock()
        self.uuids.new.side_effect = uuid4
        self.usage = Mock()
        self.usage.used = AsyncMock(return_value=())
        self.handler = EmptyTrashHandler(
            self.files, self.queries, self.queue, self.clock, self.uuids, self.usage
        )

    def file(self, *, deleted: datetime | None = None) -> StoredFile:
        """Создаёт файл в корзине через фабрику и методы Domain."""
        file = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=EntityIdVO.from_value(uuid4()),
            name=FileNameVO("file.txt"),
            content_type="text/plain",
            size=FileSizeVO(4),
            created_at=self.now - timedelta(days=60),
        )
        file.mark_uploaded(4)
        file.move_to_trash(EntityIdVO.from_value(uuid4()), deleted or self.cutoff)
        return file

    async def test_request_captures_cutoff_and_schedules_durable_job(self) -> None:
        """HTTP-сценарий сохраняет один проход без чтения реестра и физического I/O."""
        result = await RequestTrashEmptyHandler(
            self.queue, self.clock, self.uuids
        ).execute(RequestTrashEmptyCommand(self.tenant, uuid4()))
        self.assertEqual(result.cutoff, self.now)
        self.queue.schedule_empty.assert_awaited_once_with(
            self.tenant, result.job_id, self.now
        )

    async def test_candidate_changes_are_rechecked_under_lock(self) -> None:
        """Исчезнувшие, восстановленные, новые удаления и purging не затрагиваются."""
        old = self.file(deleted=self.now - timedelta(days=31))
        restored = self.file()
        restored.restore_from_trash(self.now)
        new = self.file(deleted=self.now)
        purging = self.file()
        purging.request_purge(self.now, EntityIdVO.from_value(uuid4()))
        missing = uuid4()
        records = {file.id.uuid: file for file in (old, restored, new, purging)}
        ids = [*records, missing]
        self.queries.empty_trash_candidates.return_value = tuple(
            EmptyTrashCandidateDTO(id) for id in ids
        )

        def load(identifier: EntityIdVO) -> StoredFile:
            """Моделирует актуальное состояние после блокировки."""
            if identifier.uuid == missing:
                raise FileNotFoundError()
            return records[identifier.uuid]

        self.files.get_for_update.side_effect = load
        result = await self.handler.execute(EmptyTrashCommand(self.tenant, self.cutoff))
        self.assertEqual(result.queued_count, 1)
        self.assertIsNone(result.next_after_id)
        self.assertEqual(old.status, StoredFileStatus.PURGING)
        self.files.save.assert_awaited_once_with(old)
        self.queue.schedule.assert_awaited_once_with(
            self.tenant, old.id.uuid, old.purge_job_id.uuid, self.now
        )
        self.assertEqual(new.status, StoredFileStatus.TRASHED)
        self.assertEqual(restored.status, StoredFileStatus.READY)

    async def test_cursor_advances_even_when_candidates_disappear(self) -> None:
        """Полная порция пропущенных ID не прекращает проход остальных страниц."""
        ids = sorted(uuid4() for _ in range(100))
        self.queries.empty_trash_candidates.return_value = tuple(
            EmptyTrashCandidateDTO(id) for id in ids
        )
        self.files.get_for_update.side_effect = FileNotFoundError()
        result = await self.handler.execute(EmptyTrashCommand(self.tenant, self.cutoff))
        self.assertEqual((result.queued_count, result.next_after_id), (0, ids[-1]))
        self.queue.schedule.assert_not_awaited()

    async def test_invalid_batch_and_naive_cutoff_fail_before_query(self) -> None:
        """Ограничения процесса не позволяют неограниченную порцию или неясный cutoff."""
        for size in (0, 101, True):
            with self.assertRaises(ValueError):
                await self.handler.execute(
                    EmptyTrashCommand(self.tenant, self.cutoff, batch_size=size)
                )
        with self.assertRaises(ValueError):
            await self.handler.execute(
                EmptyTrashCommand(self.tenant, self.cutoff.replace(tzinfo=None))
            )
        self.queries.empty_trash_candidates.assert_not_awaited()
