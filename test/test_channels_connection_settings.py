"""Типизированные настройки подключения и разделение публичного/SQL документов."""

from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
import json
import unittest

from pydantic import ValidationError

from test import test_channels_domain as support
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.channel.error import InvalidChannelStateError
from src.modules.channels.domain.channel.value_object.channel_name import ChannelNameVO
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.channel.value_object.stock_sync_settings import (
    StockSyncSettingsVO,
)
from src.modules.channels.infrastructure.channel.persistence.mapper import (
    to_domain,
    to_read_row,
    write_verification,
)
from src.modules.channels.infrastructure.channel.persistence.settings import (
    platform_settings,
    public_settings,
    read_stock_sync_settings,
    write_settings,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.channel.http.request.update_channel import (
    UpdateChannelRequest,
)
from src.modules.channels.presentation.channel.http.response.channel_fields import (
    ChannelResponseFields,
)


class ConnectionSettingsTests(unittest.TestCase):
    """Проверяет состояние без БД и обращений к площадкам."""

    def setUp(self) -> None:
        """Создаёт согласованный агрегат с точным временем настройки."""
        fixture = support.ChannelsDomainTests()
        fixture.setUp()
        self.channel = fixture.channel
        self.now = fixture.now

    def test_invalid_value_and_metadata_types_are_rejected(self) -> None:
        """Строки, числа и naive datetime не подменяют типизированные значения."""
        valid = dict(allow_export=False, revision=1, changed_at=self.now)
        for changes in (
            {"allow_export": 0},
            {"allow_export": "false"},
            {"revision": 0},
            {"revision": True},
            {"changed_at": self.now.replace(tzinfo=None)},
            {"changed_at": "now"},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidChannelStateError),
            ):
                StockSyncSettingsVO(**(valid | changes))
        for changes in (
            {"allow_export": "false"},
            {"revision": "1"},
            {"revision": True},
            {"extra": 1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                read_stock_sync_settings({"stock_sync": {**valid, **changes}})

    def test_policy_and_access_change_is_atomic(self) -> None:
        """Ошибка конфигурации не оставляет включённое разрешение или новое имя."""
        before = deepcopy(self.channel)
        with self.assertRaises(InvalidChannelStateError):
            self.channel.change_settings(
                expected_revision=1,
                name=ChannelNameVO("Changed"),
                config="invalid",
                encrypted_credentials=None,
                job_id=self.channel.connection.verification.job_id,
                actor_id=self.channel.updated_by,
                now=self.now,
                allow_export=True,
            )
        self.assertEqual(self.channel, before)
        changed = self.channel.change_settings(
            expected_revision=1,
            name=ChannelNameVO("Changed"),
            config=None,
            encrypted_credentials=None,
            job_id=self.channel.connection.verification.job_id,
            actor_id=self.channel.updated_by,
            now=self.now + timedelta(seconds=1),
            allow_export=True,
        )
        self.assertFalse(changed)
        self.assertEqual(self.channel.revision, 2)
        self.assertEqual(self.channel.connection.config_revision, 1)
        self.assertEqual(self.channel.connection.stock_sync.revision, 2)

    def test_sql_roundtrip_hides_metadata_and_preserves_platform_settings(self) -> None:
        """Mapper восстанавливает Connection; HTTP не выдаёт служебные поля."""
        channel = self.channel
        config = {"nested": {"ids": [1, 2]}, "currency": "UAH"}
        document = json.loads(
            json.dumps(write_settings(config, channel.connection.stock_sync))
        )
        self.assertEqual(platform_settings(document), config)
        row = ChannelModel(
            id=channel.id.uuid,
            name=channel.name.value,
            platform_kind=channel.platform_kind,
            revision=channel.revision,
            created_by=channel.created_by.uuid,
            updated_by=channel.updated_by.uuid,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
        )
        connection = ConnectionModel(
            id=channel.connection.id.uuid,
            channel_id=channel.id.uuid,
            config_version=1,
            endpoint=channel.connection.config.endpoint,
            settings=document,
            config_revision=1,
            encrypted_credentials=b"encrypted",
            identity_namespace=None,
            identity_key=None,
            verification=write_verification(channel.connection.verification),
        )
        restored = to_domain(row, connection)
        self.assertEqual(restored.connection.stock_sync, channel.connection.stock_sync)
        document["nested"]["ids"].append(3)
        self.assertEqual(restored.connection.config.settings, config)
        output = restored.connection.config.settings
        output["nested"]["ids"].append(4)
        self.assertEqual(restored.connection.config.settings, config)
        response = ChannelResponseFields.model_validate(
            asdict(to_read_row(row, connection))
        ).model_dump(mode="json")
        self.assertNotIn("allow_stock_export", response)
        self.assertEqual(
            response["config"]["settings"]["stock_sync"], {"allow_export": False}
        )
        self.assertEqual(
            public_settings(connection.settings)["stock_sync"], {"allow_export": False}
        )
        self.assertFalse(
            {"allow_stock_export", "stock_policy_revision", "stock_policy_changed_at"}
            & set(ChannelModel.__table__.columns.keys())
        )

    def test_platform_contracts_accept_only_public_stock_settings(self) -> None:
        """Все три пакета имеют одинаковую строгую публичную границу."""
        endpoints = {
            "prom": "https://my.prom.ua",
            "rozetka": "https://api-seller.rozetka.com.ua",
            "woocommerce": "https://shop.example",
        }
        for kind, endpoint in endpoints.items():
            platform = InstalledPlatforms().get(kind)
            for allowed in (False, True):
                with self.subTest(kind=kind, allowed=allowed):
                    validated = platform.validate(
                        ConnectionConfigVO.create(
                            version=1,
                            endpoint=endpoint,
                            settings={"stock_sync": {"allow_export": allowed}},
                        ),
                        None,
                    )
                    self.assertEqual(validated.allow_stock_export, allowed)
                    self.assertNotIn("stock_sync", validated.config.settings)
            for settings in (
                {"allow_export": "false"},
                {"allow_export": 1},
                {"allow_export": None},
                {"allow_export": False, "revision": 1},
                {"allow_export": False, "changed_at": self.now.isoformat()},
            ):
                with (
                    self.subTest(kind=kind, settings=settings),
                    self.assertRaises(ChannelInputError),
                ):
                    platform.validate(
                        ConnectionConfigVO.create(
                            version=1,
                            endpoint=endpoint,
                            settings={"stock_sync": settings},
                        ),
                        None,
                    )
            schema = platform.manifest.config_schema
            self.assertEqual(
                set(schema["$defs"]["StockSyncSettings"]["properties"]),
                {"allow_export"},
            )
            self.assertFalse(
                platform.validate(
                    ConnectionConfigVO.create(
                        version=1, endpoint=endpoint, settings={}
                    ),
                    None,
                ).allow_stock_export
            )
        with self.assertRaises(ValidationError):
            UpdateChannelRequest(expected_revision=1, allow_stock_export=True)
