"""Инварианты Channel, конфигурации и безопасное изменение настроек."""

import ast
import unittest
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from cryptography.fernet import Fernet
from jsonschema import Draft202012Validator
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.error import InvalidChannelError
from src.modules.channels.application.error import (
    ChannelValidationError,
    ChannelConfigConflictError,
    ChannelSecretsUnavailableError,
)
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.value_object.kind import ChannelKind
from src.modules.channels.domain.value_object.status import ChannelStatus
from src.modules.channels.domain.value_object.settings import ConnectionSettings
from src.modules.channels.infrastructure.crypto.cipher import ChannelSecretCipher
from src.modules.channels.infrastructure.definitions.registry import CodeChannelRegistry
from src.modules.channels.infrastructure.validation.connection import (
    JsonSchemaConnectionValidator,
)
from src.modules.channels.application.settings import seal_settings
from src.modules.channels.application.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.application.command.create_channel.handler import (
    CreateChannelHandler,
)
from src.modules.channels.application.command.update_channel.command import (
    UpdateChannelCommand,
)
from src.modules.channels.application.command.update_channel.handler import (
    UpdateChannelHandler,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.mapper import (
    ChannelMapper,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.config.feature.channels_config import ChannelsSettings


class ChannelsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.registry = CodeChannelRegistry()
        self.validator = JsonSchemaConnectionValidator()
        self.cipher = ChannelSecretCipher(Fernet.generate_key().decode())
        self.actor, self.tenant = uuid4(), uuid4()
        self.now = datetime(2026, 10, 6, tzinfo=UTC)
        self.clock = SimpleNamespace(now=lambda: self.now + timedelta(seconds=1))
        self.settings = seal_settings(
            self.registry.get("prom"), {"api_key": "test-secret"}, self.cipher
        )
        self.channel = Channel.create(
            channel_id=ChannelIdVO.from_value(uuid4()),
            name=" Store ",
            kind=ChannelKind.PROM,
            config_version=1,
            settings=self.settings,
            is_active=True,
            actor_id=EntityIdVO(self.actor),
            now=self.now,
        )
        self.repo = SimpleNamespace(
            add=AsyncMock(),
            get_for_update=AsyncMock(return_value=self.channel),
            save=AsyncMock(),
        )
        self.update = UpdateChannelHandler(
            self.repo, self.registry, self.validator, self.cipher, self.clock
        )

    def test_registry_is_complete_and_mutations_do_not_escape(self):
        definitions = self.registry.list_all()
        self.assertEqual(len(definitions), 21)
        self.assertEqual({d.kind for d in definitions}, set(ChannelKind))
        self.assertEqual(
            {d.kind for d in definitions if d.can_configure},
            {ChannelKind.PROM, ChannelKind.WOOCOMMERCE},
        )
        for d in definitions:
            self.assertEqual(d.config["capabilities"], {})
            if d.can_configure:
                connection = d.config["connection"]
                Draft202012Validator.check_schema(connection["json_schema"])
                self.assertEqual(
                    set(connection["json_schema"]["properties"]),
                    {f["property"] for f in connection["ui_schema"]},
                )
            else:
                self.assertIsNone(d.config["connection"])
                self.assertTrue(d.unavailable_reason)
        definitions[3].config["connection"]["json_schema"]["properties"].clear()
        self.assertIn(
            "api_key",
            self.registry.get("prom").config["connection"]["json_schema"]["properties"],
        )

    def test_aggregate_is_immutable_and_keeps_status_independent(self):
        self.assertEqual(self.channel.name, "Store")
        self.assertEqual(self.channel.status, ChannelStatus.UNVERIFIED)
        with self.assertRaises(FrozenInstanceError):
            self.channel.kind = ChannelKind.ETSY
        with self.assertRaises(TypeError):
            self.channel.settings.public["x"] = "y"
        connected = self.restore(status=ChannelStatus.CONNECTED)
        changed = connected.rename(
            "Other", actor_id=EntityIdVO(self.actor), now=self.clock.now()
        ).set_active(False, actor_id=EntityIdVO(self.actor), now=self.clock.now())
        self.assertEqual(changed.status, ChannelStatus.CONNECTED)
        self.assertFalse(changed.is_active)
        self.assertIs(
            changed.change_settings(
                changed.settings,
                1,
                actor_id=EntityIdVO(self.actor),
                now=self.clock.now(),
            ),
            changed,
        )
        with self.assertRaises(InvalidChannelError):
            self.channel.rename(" ", actor_id=EntityIdVO(self.actor), now=self.now)
        with self.assertRaises(InvalidChannelError):
            self.channel.set_active(1, actor_id=EntityIdVO(self.actor), now=self.now)

    def test_encryption_and_persistence_roundtrip(self):
        values = ChannelMapper.to_insert_values(self.channel)
        self.assertNotIn("test-secret", repr(values))
        self.assertNotIn("test-secret", repr(self.channel))
        self.assertEqual(
            self.cipher.decrypt(values["encrypted_secrets"]), {"api_key": "test-secret"}
        )
        restored = ChannelMapper.to_domain(ChannelModel(**values))
        self.assertEqual(restored, self.channel)
        with self.assertRaises(ChannelSecretsUnavailableError):
            ChannelSecretCipher("").encrypt({"x": "secret"})
        with self.assertRaises(ChannelSecretsUnavailableError):
            ChannelSecretCipher(Fernet.generate_key().decode()).decrypt(
                values["encrypted_secrets"]
            )

    def test_cipher_configuration(self):
        key = Fernet.generate_key().decode()
        self.assertEqual(
            ChannelsSettings(secret_encryption_key=key).secret_encryption_key, key
        )
        for bad in ["invalid", "abc", "ф"]:
            with self.assertRaises(ValueError):
                ChannelsSettings(secret_encryption_key=bad)
        with self.assertRaises(ValueError):
            ChannelsSettings(secret_encryption_key=key, encryption_key_path="/missing")

    def test_schema_validation_does_not_echo_credentials(self):
        for settings in [
            {},
            {"api_key": ""},
            {"api_key": None},
            {"api_key": "secret", "extra": "secret"},
            {"api_key": 123},
        ]:
            with self.subTest(settings_type=type(settings)):
                with self.assertRaises(ChannelValidationError) as caught:
                    self.validator.validate(self.registry.get("prom"), settings)
                self.assertNotIn("secret", str(caught.exception.errors))
        woo = self.registry.get("woocommerce")
        for url in [
            "http://example.com",
            "https://user:pass@example.com",
            "https://example.com?key=x",
            "https://example.com#x",
            "https://example.com:99999",
            "https://example.com/a b",
            "https://example.com\\evil",
        ]:
            with self.subTest(url=url), self.assertRaises(ChannelValidationError):
                self.validator.validate(
                    woo, dict(url=url, consumer_key="key", consumer_secret="secret")
                )
        self.validator.validate(
            woo,
            dict(
                url="https://example.com/shop/",
                consumer_key="key",
                consumer_secret="secret",
            ),
        )

    async def test_partial_update_preserves_secret_and_noop_preserves_status(self):
        self.repo.get_for_update.return_value = self.restore(
            status=ChannelStatus.CONNECTED
        )
        await self.update.execute(
            UpdateChannelCommand(
                self.tenant,
                self.actor,
                self.channel.id.uuid,
                name="Renamed",
                is_active=False,
            )
        )
        updated = self.repo.save.call_args.args[0]
        self.assertEqual(updated.settings, self.channel.settings)
        self.assertEqual(updated.status, ChannelStatus.CONNECTED)
        await self.update.execute(
            UpdateChannelCommand(
                self.tenant,
                self.actor,
                self.channel.id.uuid,
                config_version=1,
                connection_settings={"api_key": "test-secret"},
            )
        )
        self.assertEqual(
            self.repo.save.call_args.args[0].status, ChannelStatus.CONNECTED
        )
        await self.update.execute(
            UpdateChannelCommand(
                self.tenant,
                self.actor,
                self.channel.id.uuid,
                config_version=1,
                connection_settings={"api_key": "replacement"},
            )
        )
        updated = self.repo.save.call_args.args[0]
        self.assertEqual(updated.status, ChannelStatus.UNVERIFIED)
        self.assertEqual(
            self.cipher.decrypt(updated.settings.encrypted_secrets)["api_key"],
            "replacement",
        )

    async def test_validation_conflicts_do_not_write(self):
        for kwargs, error in [
            (
                {"config_version": 2, "connection_settings": {"api_key": "x"}},
                ChannelConfigConflictError,
            ),
            (
                {"config_version": 1, "connection_settings": {"api_key": ""}},
                ChannelValidationError,
            ),
            ({"connection_settings": {"api_key": "x"}}, ChannelValidationError),
        ]:
            with self.assertRaises(error):
                await self.update.execute(
                    UpdateChannelCommand(
                        self.tenant, self.actor, self.channel.id.uuid, **kwargs
                    )
                )
        self.repo.save.assert_not_awaited()

    async def test_no_key_needed_for_rename_and_activity(self):
        self.update = UpdateChannelHandler(
            self.repo,
            self.registry,
            self.validator,
            ChannelSecretCipher(""),
            self.clock,
        )
        await self.update.execute(
            UpdateChannelCommand(
                self.tenant,
                self.actor,
                self.channel.id.uuid,
                name="Other",
                is_active=False,
            )
        )
        self.repo.save.assert_awaited_once()

    async def test_creation_and_disabled_platform(self):
        create = CreateChannelHandler(
            self.repo,
            self.registry,
            self.validator,
            self.cipher,
            self.clock,
            SimpleNamespace(new=uuid4),
        )
        await create.execute(
            CreateChannelCommand(
                self.tenant, self.actor, "Prom", "prom", 1, {"api_key": "key"}
            )
        )
        self.assertEqual(
            self.repo.add.call_args.args[0].status, ChannelStatus.UNVERIFIED
        )
        with self.assertRaises(InvalidChannelError):
            await create.execute(
                CreateChannelCommand(self.tenant, self.actor, "Shop", "shopify", 1, {})
            )

    def test_dependencies_point_inward(self):
        root = Path(__file__).resolve().parents[1] / "src/modules/channels"
        forbidden = (
            "sqlalchemy",
            "fastapi",
            "pydantic",
            "jsonschema",
            "cryptography",
            "src.modules.channels.infrastructure",
            "src.modules.channels.presentation",
        )
        for layer in ["domain", "application"]:
            for file in (root / layer).rglob("*.py"):
                tree = ast.parse(file.read_text())
                for node in ast.walk(tree):
                    names = (
                        [node.module or ""]
                        if isinstance(node, ast.ImportFrom)
                        else (
                            [a.name for a in node.names]
                            if isinstance(node, ast.Import)
                            else []
                        )
                    )
                    for name in names:
                        self.assertFalse(name.startswith(forbidden), (file, name))
                    if isinstance(node, ast.Call) and isinstance(
                        node.func, ast.Attribute
                    ):
                        self.assertNotIn(node.func.attr, ("commit", "rollback"))

    def restore(self, **changes):
        state = {
            field.name: getattr(self.channel, field.name) for field in fields(Channel)
        }
        return Channel.restore(**(state | changes))

    def test_factories_validate_state_without_post_init(self):
        restored = self.restore(status=ChannelStatus.CONNECTED)
        self.assertEqual(restored.status, ChannelStatus.CONNECTED)
        self.assertEqual(restored.created_at, self.channel.created_at)
        self.assertEqual(restored.created_by, self.channel.created_by)
        for state in [
            {"id": EntityIdVO(uuid4())},
            {"name": " "},
            {"name": "x" * 256},
            {"kind": "prom"},
            {"status": "connected"},
            {"settings": {}},
            {"config_version": True},
            {"config_version": 0},
            {"is_active": 1},
            {"created_by": ChannelIdVO(uuid4())},
            {"updated_at": self.now.replace(tzinfo=None)},
        ]:
            with (
                self.subTest(fields=tuple(state)),
                self.assertRaises(InvalidChannelError),
            ):
                self.restore(**state)
        self.assertEqual(self.restore(name="  " + "x" * 255 + "  ").name, "x" * 255)
        with self.assertRaises(InvalidChannelError):
            Channel.create(
                channel_id=ChannelIdVO(uuid4()),
                name=" ",
                kind=ChannelKind.PROM,
                config_version=1,
                settings=self.settings,
                actor_id=EntityIdVO(self.actor),
                now=self.now,
            )

    def test_domain_methods_validate_transitions_and_audit(self):
        other_actor = EntityIdVO(uuid4())
        changed = self.channel.rename(
            "Renamed", actor_id=other_actor, now=self.clock.now()
        )
        self.assertEqual(changed.updated_by, other_actor)
        self.assertEqual(changed.updated_at, self.clock.now())
        self.assertEqual(changed.created_by, self.channel.created_by)
        self.assertEqual(changed.created_at, self.channel.created_at)
        self.assertEqual(self.channel.name, "Store")
        for settings, version in [(None, 1), (self.settings, 0), (self.settings, True)]:
            with self.assertRaises(InvalidChannelError):
                changed.change_settings(
                    settings, version, actor_id=other_actor, now=self.now
                )
        with self.assertRaises(InvalidChannelError):
            changed.set_active(False, actor_id=ChannelIdVO(uuid4()), now=self.now)
        with self.assertRaises(InvalidChannelError):
            changed.rename(
                "Valid name", actor_id=other_actor, now=self.now.replace(tzinfo=None)
            )

    def test_validation_issues_are_transport_independent_and_unique(self):
        with self.assertRaises(ChannelValidationError) as caught:
            self.validator.validate(self.registry.get("woocommerce"), {})
        issues = caught.exception.errors
        self.assertEqual(len(issues), 3)
        self.assertEqual(
            {issue.path for issue in issues},
            {
                ("connection_settings", "url"),
                ("connection_settings", "consumer_key"),
                ("connection_settings", "consumer_secret"),
            },
        )
        self.assertTrue(all(issue.code == "required" for issue in issues))

    async def test_command_results_are_specific_dtos_without_ciphertext(self):
        from src.modules.channels.application.command.create_channel.dto import (
            CreateChannelResultDTO,
        )
        from src.modules.channels.application.command.update_channel.dto import (
            UpdateChannelResultDTO,
        )

        create = CreateChannelHandler(
            self.repo,
            self.registry,
            self.validator,
            self.cipher,
            self.clock,
            SimpleNamespace(new=uuid4),
        )
        created = await create.execute(
            CreateChannelCommand(
                self.tenant,
                self.actor,
                "Prom",
                "prom",
                1,
                {"api_key": "result-secret"},
            )
        )
        self.assertIs(type(created), CreateChannelResultDTO)
        self.assertEqual(created.id, self.repo.add.call_args.args[0].id.uuid)
        self.assertEqual(created.type, "marketplace")
        self.assertEqual(created.configured_secret_fields, ("api_key",))
        updated = await self.update.execute(
            UpdateChannelCommand(
                self.tenant,
                self.actor,
                self.channel.id.uuid,
                name="Updated",
            )
        )
        self.assertIs(type(updated), UpdateChannelResultDTO)
        self.assertEqual(updated.name, "Updated")
        for result in [created, updated]:
            self.assertNotIn("result-secret", repr(result))
            self.assertFalse(hasattr(result, "encrypted_secrets"))
            self.assertEqual(result.connection_settings, {})
