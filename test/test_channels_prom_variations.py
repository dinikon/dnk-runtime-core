"""Наследование описаний вариации Prom без подмены остальных данных товара."""

import unittest
from unittest.mock import AsyncMock
from src.modules.channels.application.plugin_contract import (
    ConnectionCredentialsDTO,
    HttpResultDTO,
    ReadPublicationDetailsInputDTO,
    ResourceSettingsDTO,
)
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.infrastructure.plugin.prom.read_publication_details import (
    PromReadPublicationDetailsPlugin,
)


class PromVariationDetailsTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет REST-связь с основной карточкой и отдельные переводы."""

    def setUp(self) -> None:
        """Создаёт вариацию с пустым описанием и полноценную основную карточку."""
        self.credentials = AsyncMock()
        self.credentials.resolve.return_value = ConnectionCredentialsDTO(
            {"token": "test"}
        )
        self.request = ReadPublicationDetailsInputDTO(
            ResourceSettingsDTO(
                "https://my.prom.ua", {"locales": ["ru", "uk"], "currency": "UAH"}
            ),
            "company:1000",
            "product",
            "2238346131",
        )
        self.child = {
            "id": 2238346131,
            "name": "Вариация",
            "name_multilang": {"ru": "Вариация", "uk": "Варіація"},
            "description": "",
            "description_multilang": {"ru": "", "uk": ""},
            "is_variation": True,
            "variation_base_id": 661657915,
            "variation_group_id": 727381738,
            "price": 120,
            "currency": "UAH",
            "quantity_in_stock": 5,
            "main_image": "https://images.prom.ua/5919043104_w200_h200_product.jpg",
        }
        self.parent = {
            "id": 661657915,
            "is_variation": False,
            "variation_group_id": 727381738,
            "description_multilang": {
                "ru": "<p>Русское описание</p>",
                "uk": "<p>Український опис</p><script>bad()</script>",
            },
            "price": 999,
            "main_image": "https://images.prom.ua/100_w200_h200_parent.jpg",
        }

    async def test_inherits_only_missing_descriptions_in_the_same_locale(self) -> None:
        """Сохраняет фото, цену и названия вариации, получая оба описания от base ID."""
        http = AsyncMock()
        http.get.side_effect = [
            HttpResultDTO({"product": self.child}, {}),
            HttpResultDTO({"product": self.parent}, {}),
        ]
        result = await PromReadPublicationDetailsPlugin(self.credentials, http).execute(
            self.request
        )
        self.assertEqual(
            [(t.title, t.body) for t in result.translations],
            [
                ("Вариация", "<p>Русское описание</p>"),
                ("Варіація", "<p>Український опис</p>"),
            ],
        )
        self.assertEqual(result.core.price, 120)
        self.assertEqual(result.core.quantity, 5)
        self.assertEqual(
            result.images[0].url, "https://images.prom.ua/5919043104_product.jpg"
        )
        self.assertIn("description_inherited_from_parent", result.warnings)
        self.assertEqual(
            [call.args[0] for call in http.get.await_args_list],
            ["/api/v1/products/2238346131", "/api/v1/products/661657915"],
        )

    async def test_own_translation_is_preserved_and_complete_card_does_not_fetch_base(
        self,
    ) -> None:
        """Наследование не заменяет введённый перевод и не делает лишний GET."""
        self.child["description_multilang"]["ru"] = "<p>Своё описание</p>"
        for uk_body, expected_calls in (("", 2), ("<p>Свій опис</p>", 1)):
            with self.subTest(uk_body=uk_body):
                self.child["description_multilang"]["uk"] = uk_body
                http = AsyncMock()
                http.get.side_effect = [
                    HttpResultDTO({"product": self.child}, {}),
                    HttpResultDTO({"product": self.parent}, {}),
                ]
                result = await PromReadPublicationDetailsPlugin(
                    self.credentials, http
                ).execute(self.request)
                self.assertEqual(result.translations[0].body, "<p>Своё описание</p>")
                self.assertEqual(http.get.await_count, expected_calls)

    async def test_rejects_wrong_base_identity_group_and_recursive_parent(self) -> None:
        """Чужая карточка и цепочка вариаций не становятся источником текста."""
        for overrides in (
            {"id": 42},
            {"id": 661657915.0},
            {"variation_group_id": 42},
            {"is_variation": True},
        ):
            with self.subTest(overrides=overrides):
                http = AsyncMock()
                http.get.side_effect = [
                    HttpResultDTO({"product": self.child}, {}),
                    HttpResultDTO({"product": {**self.parent, **overrides}}, {}),
                ]
                with self.assertRaises(PluginCallError) as error:
                    await PromReadPublicationDetailsPlugin(
                        self.credentials, http
                    ).execute(self.request)
                self.assertEqual(
                    error.exception.reason_code, "invalid_publication_parent"
                )
