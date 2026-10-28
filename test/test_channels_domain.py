"""Инварианты, атомарность изменений и изоляция настроек Channels."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import unittest
from uuid import uuid4

from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.connection import Connection
from src.modules.channels.domain.channel.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.channel.error import (
    InvalidChannelNameError,
    InvalidChannelStateError,
    InvalidResourceIdentityError,
)
from src.modules.channels.domain.channel.value_object.channel_name import ChannelNameVO
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.channel.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.domain.channel.value_object.verification import VerificationVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ChannelsDomainTests(unittest.TestCase):
    """Проверяет жизненный цикл агрегата независимо от HTTP и SQL."""

    def setUp(self) -> None:
        """Создаёт новое подключение с первой ожидающей проверкой."""
        self.now = datetime.now(UTC)
        self.actor = EntityIdVO(uuid4())
        self.job = EntityIdVO(uuid4())
        self.config = ConnectionConfigVO.create(
            version=1, endpoint="https://my.prom.ua", settings={}
        )
        self.connection = Connection.create(
            connection_id=EntityIdVO(uuid4()),
            config=self.config,
            encrypted_credentials=b"encrypted",
            job_id=self.job,
        )
        self.channel = Channel.create(
            channel_id=EntityIdVO(uuid4()),
            name=ChannelNameVO(" Shop "),
            platform_kind="prom",
            connection=self.connection,
            actor_id=self.actor,
            now=self.now,
        )
        self.identity = ResourceIdentityVO(namespace="prom.root_group", key="1")

    def test_settings_revision_matrix(self) -> None:
        """Одно изменение имени и доступа увеличивает ревизию корня один раз."""
        changed_config = ConnectionConfigVO.create(
            version=1, endpoint=self.config.endpoint, settings={"nested": [1]}
        )
        for name, config, credentials, revisions, changed in (
            (None, self.config, None, (1, 1), False),
            (ChannelNameVO("Shop"), self.config, None, (1, 1), False),
            (ChannelNameVO("New"), None, None, (2, 1), False),
            (None, changed_config, None, (2, 2), True),
            (None, None, b"replacement", (2, 2), True),
            (ChannelNameVO("New"), changed_config, b"replacement", (2, 2), True),
        ):
            with self.subTest(name=name, config=config, credentials=credentials):
                channel = deepcopy(self.channel)
                job, actor = EntityIdVO(uuid4()), EntityIdVO(uuid4())
                now = self.now + timedelta(seconds=1)
                result = channel.change_settings(
                    expected_revision=1,
                    name=name,
                    config=config,
                    encrypted_credentials=credentials,
                    job_id=job,
                    actor_id=actor,
                    now=now,
                )
                self.assertEqual(result, changed)
                self.assertEqual(
                    (channel.revision, channel.connection.config_revision), revisions
                )
                self.assertEqual(
                    channel.updated_at, now if revisions[0] == 2 else self.now
                )
                self.assertEqual(
                    channel.updated_by, actor if revisions[0] == 2 else self.actor
                )
                self.assertEqual(
                    channel.connection.verification.job_id, job if changed else self.job
                )

    def test_snapshot_copies_nested_input_and_output(self) -> None:
        """Вложенные словари и списки не позволяют изменить конфигурацию извне."""
        source = {"groups": [{"ids": [1, 2]}]}
        config = ConnectionConfigVO.create(
            version=1, endpoint="https://shop.example", settings=source
        )
        source["groups"][0]["ids"].append(3)
        output = config.settings
        output["groups"][0]["ids"].clear()
        self.assertEqual(config.settings, {"groups": [{"ids": [1, 2]}]})

    def test_invalid_changes_leave_aggregate_untouched(self) -> None:
        """Ошибки настроек, контекста и поколения не оставляют частичных изменений."""
        valid = dict(
            expected_revision=1,
            name=ChannelNameVO("New"),
            config=None,
            encrypted_credentials=b"replacement",
            job_id=self.job,
            actor_id=self.actor,
            now=self.now,
        )
        for invalid in (
            {"config": {}},
            {"encrypted_credentials": b""},
            {"job_id": None},
            {"actor_id": None},
            {"now": None},
            {"name": "raw name"},
        ):
            with self.subTest(invalid=invalid):
                before = deepcopy(self.channel)
                with self.assertRaises(InvalidChannelStateError):
                    self.channel.change_settings(**(valid | invalid))
                self.assertEqual(self.channel, before)

    def test_invalid_results_leave_pending_state_untouched(self) -> None:
        """Identity, причина и время проверяются до изменения подключения."""
        valid = dict(
            job_id=self.job,
            config_revision=1,
            identity=self.identity,
            error_code=None,
            now=self.now,
        )
        for invalid, error in (
            ({"identity": None}, InvalidResourceIdentityError),
            ({"identity": "raw"}, InvalidResourceIdentityError),
            ({"error_code": ""}, InvalidChannelStateError),
            ({"now": None}, InvalidChannelStateError),
        ):
            before = deepcopy(self.channel)
            with self.subTest(invalid=invalid), self.assertRaises(error):
                self.channel.apply_verification(**(valid | invalid))
            self.assertEqual(self.channel, before)

    def test_reverification_pins_identity_and_ignores_old_generations(self) -> None:
        """Повторная проверка сохраняет доступ и identity, отбрасывая старый результат."""
        self.channel.apply_verification(
            job_id=self.job,
            config_revision=1,
            identity=self.identity,
            error_code=None,
            now=self.now,
        )
        self.assertEqual(self.channel.revision, 2)
        self.assertTrue(self.channel.can_confirm_identity(self.identity))
        other = ResourceIdentityVO(namespace=self.identity.namespace, key="2")
        self.assertFalse(self.channel.can_confirm_identity(other))
        next_job = EntityIdVO(uuid4())
        self.channel.request_verification(
            job_id=next_job, actor_id=self.actor, now=self.now
        )
        before = deepcopy(self.channel)
        self.channel.apply_verification(
            job_id=self.job, config_revision=1, identity=None, error_code=None, now=None
        )
        self.assertEqual(self.channel, before)
        self.channel.apply_verification(
            job_id=next_job,
            config_revision=1,
            identity=other,
            error_code=None,
            now=self.now,
        )
        self.assertEqual(self.channel.revision, 4)
        self.assertEqual(self.connection.config_revision, 1)
        self.assertEqual(self.connection.identity, self.identity)
        self.assertEqual(
            self.connection.verification.error_code, "resource_identity_changed"
        )
        before = deepcopy(self.channel)
        self.channel.apply_verification(
            job_id=next_job,
            config_revision=1,
            identity=self.identity,
            error_code=None,
            now=self.now,
        )
        self.assertEqual(self.channel, before)
        self.channel.request_verification(
            job_id=self.job, actor_id=self.actor, now=self.now
        )
        self.channel.apply_verification(
            job_id=self.job,
            config_revision=1,
            identity=self.identity,
            error_code=None,
            now=self.now,
        )
        self.assertEqual(
            self.connection.verification.status, VerificationStatus.VERIFIED
        )

    def test_verification_rejects_contradictory_documents(self) -> None:
        """Статус согласован с ревизией, временем результата и причиной отказа."""
        base = dict(job_id=self.job, config_revision=1)
        for invalid in (
            {"config_revision": 0},
            {"config_revision": -1},
            {"config_revision": True},
            {"job_id": None},
            {"status": "pending"},
            {"checked_at": self.now},
            {"error_code": "failure"},
            {"status": VerificationStatus.VERIFIED},
            {
                "status": VerificationStatus.VERIFIED,
                "checked_at": self.now,
                "error_code": "failure",
            },
            {"status": VerificationStatus.ERROR, "checked_at": self.now},
            {
                "status": VerificationStatus.ERROR,
                "checked_at": self.now,
                "error_code": " ",
            },
            {"status": VerificationStatus.ERROR, "error_code": "failure"},
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(InvalidChannelStateError),
            ):
                VerificationVO(**(base | invalid))

    def test_restore_rejects_inconsistent_connection(self) -> None:
        """Восстановление не исправляет ревизии и отсутствующую identity."""
        verified = VerificationVO(
            job_id=self.job,
            config_revision=1,
            status=VerificationStatus.VERIFIED,
            checked_at=self.now,
        )
        valid = dict(
            connection_id=self.connection.id,
            config=self.config,
            encrypted_credentials=b"encrypted",
            config_revision=1,
            identity=None,
            verification=self.connection.verification,
        )
        for invalid in (
            {"config_revision": 0},
            {"config_revision": 2},
            {"config_revision": True},
            {"verification": verified},
            {"encrypted_credentials": b""},
            {"identity": "raw"},
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(InvalidChannelStateError),
            ):
                Connection.restore(**(valid | invalid))
        restored = Connection.restore(
            **(valid | {"verification": verified, "identity": self.identity})
        )
        self.assertEqual(restored.identity, self.identity)
        with self.assertRaises(InvalidChannelStateError):
            Channel.create(
                channel_id=self.channel.id,
                name=self.channel.name,
                platform_kind="prom",
                connection=restored,
                actor_id=self.actor,
                now=self.now,
            )

    def test_channel_restore_validates_owned_entity_and_revision(self) -> None:
        """Корень отклоняет несовместимые ревизии и некорректную Entity."""
        valid = dict(
            channel_id=self.channel.id,
            name=self.channel.name,
            platform_kind="prom",
            revision=1,
            connection=self.connection,
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        for invalid in (
            {"revision": 0},
            {"revision": True},
            {"connection": None},
            {"connection": replace(self.connection, config_revision=2)},
            {"name": "raw"},
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(InvalidChannelStateError),
            ):
                Channel.restore(**(valid | invalid))
        connection = replace(
            self.connection,
            config_revision=2,
            verification=VerificationVO(job_id=self.job, config_revision=2),
        )
        with self.assertRaises(InvalidChannelStateError):
            Channel.restore(**(valid | {"connection": connection}))
        self.assertEqual(Channel.restore(**valid), self.channel)

    def test_creation_and_retry_reject_invalid_state_without_mutation(self) -> None:
        """Новый канал требует нового подключения; ошибочный retry не меняет аудит."""
        for connection in (None, replace(self.connection, identity=self.identity)):
            with (
                self.subTest(connection=connection),
                self.assertRaises(InvalidChannelStateError),
            ):
                Channel.create(
                    channel_id=self.channel.id,
                    name=self.channel.name,
                    platform_kind="prom",
                    connection=connection,
                    actor_id=self.actor,
                    now=self.now,
                )
        before = deepcopy(self.channel)
        with self.assertRaises(InvalidChannelStateError):
            self.channel.request_verification(
                job_id=None, actor_id=self.actor, now=self.now
            )
        self.assertEqual(self.channel, before)
        self.channel.apply_verification(
            job_id=self.job,
            config_revision=2,
            identity=self.identity,
            error_code=None,
            now=self.now,
        )
        self.assertEqual(self.channel, before)

    def test_names_and_identity_reject_invalid_values(self) -> None:
        """Значения содержат предметные проверки, не зависящие от транспорта."""
        for name in ("", "   ", "n" * 256, None):
            with self.subTest(name=name), self.assertRaises(InvalidChannelNameError):
                ChannelNameVO(name)
        for namespace, key in (
            ("", "1"),
            ("prom", ""),
            ("x" * 101, "1"),
            ("prom", "я" * 513),
        ):
            with (
                self.subTest(namespace=namespace),
                self.assertRaises(InvalidResourceIdentityError),
            ):
                ResourceIdentityVO(namespace=namespace, key=key)
