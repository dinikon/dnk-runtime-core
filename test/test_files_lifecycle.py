"""Правила корзины, сроков и смены заданий удаления без внешних сервисов."""

from datetime import UTC, datetime, timedelta
import unittest
from uuid import uuid4
from zoneinfo import ZoneInfo

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.error import InvalidFileError
from src.modules.files.domain.stored_file.error import (
    FileStateConflictError,
    FileTrashExpiredError,
)
from src.modules.files.domain.stored_file.aggregate import StoredFile
from src.modules.files.domain.stored_file.status import StoredFileStatus
from src.modules.files.domain.value_object.file_name import FileNameVO
from src.modules.files.domain.value_object.file_size import FileSizeVO
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.infrastructure.stored_file.persistence.mapper import (
    StoredFileMapper,
)


class StoredFileLifecycleTests(unittest.TestCase):
    """Проверяет предметные границы независимо от SQL и очереди."""

    def setUp(self) -> None:
        """Создаёт готовый файл с управляемыми датами и ID."""
        self.created = datetime(2026, 3, 1, 12, tzinfo=UTC)
        self.deleted = self.created + timedelta(days=1)
        self.actor = EntityIdVO.from_value(uuid4())
        self.job = EntityIdVO.from_value(uuid4())
        self.file = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=EntityIdVO.from_value(uuid4()),
            name=FileNameVO("report.pdf"),
            content_type="application/pdf",
            size=FileSizeVO(10),
            created_at=self.created,
        )
        self.file.mark_uploaded(10)

    def test_repeat_trash_preserves_deadline_actor_and_object(self) -> None:
        """Повторное удаление не меняет происхождение, сроки и ключ файла."""
        key = self.file.object_key
        self.file.move_to_trash(self.actor, self.deleted)
        self.file.move_to_trash(
            EntityIdVO.from_value(uuid4()), self.deleted + timedelta(days=40)
        )
        self.assertEqual(self.file.deleted_at, self.deleted)
        self.assertEqual(self.file.deleted_by, self.actor)
        self.assertEqual(self.file.purge_after, self.deleted + timedelta(hours=720))
        self.assertEqual(self.file.object_key, key)
        self.assertEqual(self.file.status, StoredFileStatus.TRASHED)

    def test_restore_boundary_and_new_retention_period(self) -> None:
        """Восстановление разрешено до границы; новый цикл начинает новый срок."""
        self.file.move_to_trash(self.actor, self.deleted)
        deadline = self.file.purge_after
        for now in (deadline, deadline + timedelta(microseconds=1)):
            with self.subTest(now=now), self.assertRaises(FileTrashExpiredError):
                self.file.restore_from_trash(now)
            self.assertEqual(self.file.status, StoredFileStatus.TRASHED)
        self.file.restore_from_trash(deadline - timedelta(microseconds=1))
        self.file.restore_from_trash(deadline)
        self.assertEqual(self.file.status, StoredFileStatus.READY)
        self.assertTrue(
            all(
                value is None
                for value in (
                    self.file.deleted_at,
                    self.file.deleted_by,
                    self.file.purge_after,
                    self.file.purge_requested_at,
                    self.file.purge_job_id,
                )
            )
        )
        self.file.move_to_trash(self.actor, deadline)
        self.assertEqual(self.file.purge_after, deadline + timedelta(days=30))

    def test_manual_purge_is_early_and_automatic_purge_waits_for_deadline(self) -> None:
        """Автоматическое удаление нельзя начать раньше срока; ручное можно."""
        self.file.move_to_trash(self.actor, self.deleted)
        deadline = self.file.purge_after
        with self.assertRaises(FileStateConflictError):
            self.file.request_expired_purge(
                deadline - timedelta(microseconds=1), self.job
            )
        self.assertIsNone(self.file.purge_job_id)
        self.file.request_expired_purge(deadline, self.job)
        self.assertEqual(self.file.status, StoredFileStatus.PURGING)
        manual = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=self.file.bucket_id,
            name=self.file.name,
            content_type=self.file.content_type,
            size=self.file.size,
            created_at=self.created,
        )
        manual.mark_uploaded(10)
        manual.move_to_trash(self.actor, self.deleted)
        manual.request_purge(self.deleted, self.job)
        self.assertEqual(manual.purge_requested_at, self.deleted)

    def test_purge_retries_replacement_and_stale_delivery(self) -> None:
        """Повтор сохраняет job; смена job блокирует прежнее подтверждение."""
        self.file.move_to_trash(self.actor, self.deleted)
        self.file.request_purge(self.deleted, self.job)
        original_deadline = self.file.purge_after
        replacement = EntityIdVO.from_value(uuid4())
        self.file.request_purge(self.deleted + timedelta(days=1), replacement)
        self.file.request_expired_purge(self.deleted + timedelta(days=31), replacement)
        self.assertEqual(self.file.purge_job_id, self.job)
        self.assertEqual(self.file.purge_requested_at, self.deleted)
        with self.assertRaises(FileStateConflictError):
            self.file.restore_from_trash(self.deleted)
        self.file.replace_purge_job(replacement)
        self.assertFalse(self.file.is_current_purge_job(self.job))
        self.assertTrue(self.file.is_current_purge_job(replacement))
        with self.assertRaises(FileStateConflictError):
            self.file.mark_purged(self.job)
        self.assertEqual(self.file.purge_after, original_deadline)
        with self.assertRaises(FileStateConflictError):
            self.file.ensure_purged()
        self.file.mark_purged(replacement)
        self.file.mark_purged(replacement)
        self.file.ensure_purged()
        with self.assertRaises(FileStateConflictError):
            self.file.replace_purge_job(self.job)

    def test_rejects_transitions_from_uploading_and_ready_purge(self) -> None:
        """Файл не попадает в корзину до загрузки и не удаляется напрямую из ready."""
        uploading = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=self.file.bucket_id,
            name=self.file.name,
            content_type=self.file.content_type,
            size=self.file.size,
            created_at=self.created,
        )
        for file in (uploading, self.file):
            for operation in (
                lambda: file.request_purge(self.deleted, self.job),
                lambda: file.request_expired_purge(self.deleted, self.job),
                lambda: file.replace_purge_job(self.job),
                lambda: file.mark_purged(self.job),
                file.ensure_purged,
            ):
                with (
                    self.subTest(status=file.status),
                    self.assertRaises(FileStateConflictError),
                ):
                    operation()
        with self.assertRaises(FileStateConflictError):
            uploading.move_to_trash(self.actor, self.deleted)
        with self.assertRaises(FileStateConflictError):
            uploading.restore_from_trash(self.deleted)
        self.file.move_to_trash(self.actor, self.deleted)
        self.file.request_purge(self.deleted, self.job)
        with self.assertRaises(FileStateConflictError):
            self.file.move_to_trash(self.actor, self.deleted)
        with self.assertRaises(InvalidFileError):
            self.file.mark_uploaded(10)

    def test_utc_retention_crosses_dst_and_rejects_naive_or_backward_time(self) -> None:
        """Срок составляет 720 часов даже при смене времени; даты валидируются."""
        local = datetime(2026, 3, 15, 12, tzinfo=ZoneInfo("Europe/Kyiv"))
        self.file.move_to_trash(self.actor, local)
        self.assertIs(self.file.deleted_at.tzinfo, UTC)
        self.assertIs(self.file.purge_after.tzinfo, UTC)
        self.assertEqual(
            self.file.purge_after - self.file.deleted_at, timedelta(hours=720)
        )
        self.assertEqual(self.file.purge_after.astimezone(local.tzinfo).hour, 13)
        for now, error in (
            (local.replace(tzinfo=None), InvalidFileError),
            (local - timedelta(seconds=1), FileStateConflictError),
        ):
            with self.subTest(now=now), self.assertRaises(error):
                self.file.restore_from_trash(now)

    def test_restore_factory_rejects_incomplete_or_inconsistent_states(self) -> None:
        """Фабрика владеет проверками комбинаций полей и порядка времён."""
        active = StoredFileMapper.to_insert_values(self.file)
        trashed = active | {
            "status": "trashed",
            "deleted_at": self.deleted,
            "deleted_by": self.actor.uuid,
            "purge_after": self.deleted + timedelta(days=30),
        }
        purging = trashed | {
            "status": "purging",
            "purge_requested_at": self.deleted,
            "purge_job_id": self.job.uuid,
        }
        invalid = [
            active | {"status": "unknown"},
            active | {"object_key": uuid4().hex},
            active | {"created_at": self.created.replace(tzinfo=None)},
            active | {"content_type": "invalid"},
            active | {"deleted_by": self.actor.uuid},
            trashed | {"purge_after": self.deleted + timedelta(days=29)},
            trashed | {"deleted_at": self.created - timedelta(seconds=1)},
            trashed | {"purge_job_id": self.job.uuid},
            trashed | {"purge_requested_at": self.deleted},
            purging | {"purge_requested_at": self.deleted - timedelta(seconds=1)},
        ]
        for key in ("deleted_at", "deleted_by", "purge_after"):
            invalid.append(trashed | {key: None})
        for key in ("purge_requested_at", "purge_job_id"):
            invalid.append(purging | {key: None})
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(InvalidFileError):
                StoredFileMapper.to_domain(StoredFileModel(**values))

    def test_mapper_round_trip_all_states_without_losing_metadata(self) -> None:
        """Маппер передаёт все данные фабрике, включая actor и job ID."""

        def round_trip() -> None:
            """Сопоставляет сохранённые и восстановленные поля."""
            row = StoredFileModel(**StoredFileMapper.to_insert_values(self.file))
            restored = StoredFileMapper.to_domain(row)
            self.assertEqual(restored, self.file)
            self.assertIsInstance(restored.status, StoredFileStatus)

        round_trip()

        uploading = StoredFile.create(
            file_id=EntityIdVO.from_value(uuid4()),
            bucket_id=self.file.bucket_id,
            name=self.file.name,
            content_type=self.file.content_type,
            size=self.file.size,
            created_at=self.created,
        )
        self.assertEqual(
            StoredFileMapper.to_domain(
                StoredFileModel(**StoredFileMapper.to_insert_values(uploading))
            ),
            uploading,
        )
        self.file.move_to_trash(self.actor, self.deleted)
        round_trip()
        self.file.request_purge(self.deleted, self.job)
        round_trip()
        self.file.mark_purged(self.job)
        round_trip()

    def test_invalid_references_leave_state_unchanged(self) -> None:
        """Некорректные actor/job ID не оставляют частично изменённый агрегат."""
        with self.assertRaises(InvalidFileError):
            self.file.move_to_trash(None, self.deleted)
        self.assertEqual(self.file.status, StoredFileStatus.READY)
        self.assertIsNone(self.file.deleted_at)
        self.file.move_to_trash(self.actor, self.deleted)
        with self.assertRaises(InvalidFileError):
            self.file.request_purge(self.deleted, None)
        self.assertEqual(self.file.status, StoredFileStatus.TRASHED)
        self.assertIsNone(self.file.purge_requested_at)
        self.file.request_purge(self.deleted, self.job)
        with self.assertRaises(InvalidFileError):
            self.file.replace_purge_job(None)
        self.assertEqual(self.file.purge_job_id, self.job)
