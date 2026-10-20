"""Контракты записи и инварианты ручного обновления существующих карточек."""

from datetime import UTC, datetime, timedelta
import unittest
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.content_update.aggregate import ContentUpdateRun
from src.modules.channels.domain.content_update.entity.item import ContentUpdateItem
from src.modules.channels.domain.content_update.value_object.texts import (
    ContentTextsVO,
    LocalizedTextVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ReadPublicationDetailsInputDTO,
    ConnectionCredentialsDTO,
    PublicationTranslationDTO,
)
from src.modules.channels.application.content_update.plugin_contract import (
    InspectContentUpdateInputDTO,
    SendContentUpdateInputDTO,
)
from src.modules.channels.application.content_update.texts import content_texts
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.infrastructure.plugin.woocommerce.update_content import (
    WooContentUpdatePlugin,
)
from src.modules.channels.infrastructure.plugin.prom.update_content import (
    PromContentUpdatePlugin,
)
from src.modules.channels.infrastructure.http.transport import ScopedHttpTransport
from test.test_channels_content_update_postgres import ContentTransport


class ContentUpdateDomainTests(unittest.TestCase):
    """Защищает подтверждение показанного снимка и отсутствие слепого повторения."""

    def run_fixture(self) -> ContentUpdateRun:
        """Готовит уже прочитанный предпросмотр одной существующей цели."""
        now = datetime.now(UTC)
        desired = ContentTextsVO((LocalizedTextVO("uk", "New", "<p>New body</p>"),))
        item = ContentUpdateItem.create(
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            1,
            "product",
            "10",
            {},
            desired,
        )
        run = ContentUpdateRun.create(
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            1,
            4,
            now,
            now + timedelta(hours=24),
            [item],
        )
        run.apply_step(
            0,
            item.publication_id,
            "preview",
            ContentTextsVO((LocalizedTextVO("uk", "Old", "<p>Old</p>"),)),
            (),
            None,
            False,
        )
        run.advance()
        return run

    def test_confirmation_hash_revision_expiration_and_replay(self) -> None:
        """Разрешён только показанный снимок; replay не принимает новый hash."""
        run = self.run_fixture()
        with self.assertRaises(ChannelsConflictError):
            run.confirm(run.revision, "wrong", datetime.now(UTC))
        with self.assertRaises(ChannelsConflictError):
            run.confirm(run.revision, run.preview_hash_value, run.expires_at)
        revision, fingerprint = run.revision, run.preview_hash_value
        self.assertTrue(run.confirm(revision, fingerprint, datetime.now(UTC)))
        self.assertFalse(run.confirm(revision, fingerprint, datetime.now(UTC)))
        with self.assertRaises(ChannelsConflictError):
            run.confirm(revision, "changed", datetime.now(UTC))

    def test_recovered_intent_is_verified_without_second_dispatch(self) -> None:
        """Sending после восстановления никогда не превращается в новый сетевой write."""
        run = self.run_fixture()
        run.confirm(run.revision, run.preview_hash_value, datetime.now(UTC))
        item, mode = run.dispatch(run.sequence)
        self.assertEqual(mode, "send")
        self.assertEqual(item.attempts, 1)
        run.recover()
        _, mode = run.dispatch(run.sequence)
        self.assertEqual(mode, "verify")
        self.assertEqual(item.attempts, 1)

    def test_locale_contract_rejects_fallback_and_duplicates(self) -> None:
        """Внешний плагин обязан вернуть точный набор настроенных локалей."""
        with self.assertRaises(ChannelsValidationError):
            content_texts(
                (PublicationTranslationDTO("ru", "Name", "Body"),), ("ru", "uk")
            )
        with self.assertRaises(ChannelsValidationError):
            ContentTextsVO(
                (
                    LocalizedTextVO("uk", "One", "Body"),
                    LocalizedTextVO("uk", "Two", "Body"),
                )
            )


class Credentials:
    """Предоставляет только fixture credentials текущего scope."""

    async def resolve(self) -> ConnectionCredentialsDTO:
        """Возвращает fake ключи без доступа к SQL и другим подключениям."""
        return ConnectionCredentialsDTO(
            {"consumer_key": "key", "consumer_secret": "secret", "token": "token"}
        )


class ContentUpdatePluginTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет реальные plugin serializers и предохранители HTTP фасада."""

    def request(
        self, kind: str = "woocommerce", resource_type: str = "product"
    ) -> InspectContentUpdateInputDTO:
        """Собирает только typed разрешённые поля операции."""
        locales = ["uk"] if kind == "woocommerce" else ["ru", "uk"]
        return InspectContentUpdateInputDTO(
            ReadPublicationDetailsInputDTO(
                ResourceSettingsDTO(
                    (
                        "https://shop.example"
                        if kind == "woocommerce"
                        else "https://my.prom.ua"
                    ),
                    {"locales": locales, "currency": "UAH"},
                ),
                "shop",
                resource_type,
                "10",
                {"parent_id": 20},
            ),
            tuple(
                PublicationTranslationDTO(locale, "Title", "<p>Body</p>")
                for locale in locales
            ),
        )

    async def test_woo_writes_only_name_description_and_existing_id(self) -> None:
        """Serializer не передаёт цену, наличие, media или команды создания."""
        transport = ContentTransport()
        plugin = WooContentUpdatePlugin(Credentials(), transport)
        request = self.request()
        inspection = await plugin.inspect(request)
        expected = content_texts(inspection.observed, ("uk",)).digest()
        await plugin.send(SendContentUpdateInputDTO(request, expected))
        self.assertEqual(
            transport.writes,
            [
                (
                    "/wp-json/wc/v3/products/10",
                    {"name": "Title", "description": "<p>Body</p>"},
                )
            ],
        )

    async def test_woo_variation_never_changes_parent_title(self) -> None:
        """Наследование входящего описания не становится разрешением записи родителю."""
        transport = ContentTransport()
        plugin = WooContentUpdatePlugin(Credentials(), transport)
        request = self.request(resource_type="variation")
        result = await plugin.inspect(request)
        self.assertIn("content_update_target_unsupported", result.issues)
        with self.assertRaises(PluginCallError):
            await plugin.send(SendContentUpdateInputDTO(request, "unused"))
        self.assertEqual(transport.writes, [])

    async def test_prom_fails_closed_even_if_send_called_directly(self) -> None:
        """Отсутствие capability нельзя обойти прямым обращением к реализации."""
        transport = ContentTransport()
        plugin = PromContentUpdatePlugin(Credentials(), transport)
        request = self.request("prom")
        result = await plugin.inspect(request)
        self.assertIn("content_update_update_only_unconfirmed", result.issues)
        with self.assertRaisesRegex(
            PluginCallError, "content_update_update_only_unconfirmed"
        ):
            await plugin.send(SendContentUpdateInputDTO(request, "unused"))
        self.assertEqual(transport.writes, [])

    async def test_http_facade_rejects_extra_fields_before_network(self) -> None:
        """Даже plugin runtime не получает произвольную запись всей карточки."""
        with self.assertRaisesRegex(PluginCallError, "invalid_content_payload"):
            await ScopedHttpTransport("https://shop.example").put(
                "/wp-json/wc/v3/products/10",
                payload={"name": "Title", "description": "Body", "price": "100"},
            )
