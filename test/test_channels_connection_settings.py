"""Контракты подключения после удаления товарных настроек Channels."""

from dataclasses import asdict
import unittest

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.infrastructure.persistence.mapper import (
    to_domain,
    to_read_row,
    write_verification,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from test import test_channels_domain as support


class ConnectionSettingsTests(unittest.TestCase):
    """Настройки больше не содержат политику записи, валюту или локали."""

    def test_removed_settings_are_rejected_by_each_concrete_package(self) -> None:
        """Старый клиент не может незаметно включить удалённые возможности."""
        for manifest in InstalledPlatforms().manifests():
            platform = InstalledPlatforms().get(manifest.kind)
            endpoint = (
                "https://shop.example"
                if manifest.kind == "woocommerce"
                else (
                    "https://my.prom.ua"
                    if manifest.kind == "prom"
                    else "https://api-seller.rozetka.com.ua"
                )
            )
            for settings in (
                {"stock_sync": {"allow_export": True}},
                {"currency": "UAH"},
                {"locales": ["uk", "ru"]},
                {"locale": "uk"},
            ):
                with (
                    self.subTest(platform=manifest.kind, settings=settings),
                    self.assertRaises(ChannelInputError),
                ):
                    platform.validate(
                        ConnectionConfigVO.create(
                            version=1, endpoint=endpoint, settings=settings
                        ),
                        None,
                    )
            valid = platform.validate(
                ConnectionConfigVO.create(version=1, endpoint=endpoint, settings={}),
                None,
            )
            self.assertEqual(valid.config.settings, {})
            self.assertEqual(
                platform.manifest.supported_capabilities, ("verify_connection",)
            )

    def test_mapper_roundtrip_has_no_retired_policy_and_preserves_secret(self) -> None:
        """Mapper восстанавливает только принадлежащие Channel данные подключения."""
        fixture = support.ChannelsDomainTests()
        fixture.setUp()
        value = fixture.channel
        row = ChannelModel(
            id=value.id.uuid,
            name=value.name.value,
            platform_kind=value.platform_kind,
            revision=value.revision,
            created_by=value.created_by.uuid,
            updated_by=value.updated_by.uuid,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )
        c = value.connection
        stored = ConnectionModel(
            id=c.id.uuid,
            channel_id=value.id.uuid,
            config_version=c.config.version,
            endpoint=c.config.endpoint,
            settings={},
            encrypted_credentials=c.encrypted_credentials,
            config_revision=c.config_revision,
            identity_namespace=None,
            identity_key=None,
            verification=write_verification(c.verification),
        )
        restored = to_domain(row, stored)
        self.assertEqual(asdict(restored), asdict(value))
        public = to_read_row(row, stored)
        self.assertEqual(public.config.settings, {})
        self.assertNotIn("credentials", repr(public))
        self.assertFalse(hasattr(restored.connection, "stock_sync"))
