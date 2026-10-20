"""Проверяет полноразмерные изображения Prom без изменений общего downloader."""

import unittest
from unittest.mock import AsyncMock
from src.modules.channels.application.plugin_contract import (
    ConnectionCredentialsDTO,
    HttpResultDTO,
    ReadPublicationDetailsInputDTO,
    ResourceSettingsDTO,
)
from src.modules.channels.infrastructure.plugin.prom.images import original_image_url
from src.modules.channels.infrastructure.plugin.prom.read_publication_details import (
    PromReadPublicationDetailsPlugin,
)


class PromImagesTests(unittest.IsolatedAsyncioTestCase):
    """Закрепляет наблюдаемый формат CDN отдельно от URL других провайдеров."""

    async def test_full_size_gallery_keeps_main_first_and_removes_size_duplicates(
        self,
    ) -> None:
        """API 200px и другой размер одного фото дают один исходный файл в галерее."""
        credentials, http = AsyncMock(), AsyncMock()
        credentials.resolve.return_value = ConnectionCredentialsDTO({"token": "test"})
        http.get.return_value = HttpResultDTO(
            {
                "product": {
                    "id": 102,
                    "name": "Товар",
                    "price": 10,
                    "currency": "UAH",
                    "main_image": "https://images.prom.ua/100_w200_h200_product.jpg",
                    "images": [
                        {
                            "id": 100,
                            "url": "https://images.prom.ua/100_w640_h640_product.jpg",
                            "thumbnail_url": "https://images.prom.ua/100_w100_h100_product.jpg",
                        },
                        {
                            "id": 200,
                            "url": "https://images.prom.ua/200_w200_h200_product_back.png",
                        },
                    ],
                }
            },
            {},
        )
        result = await PromReadPublicationDetailsPlugin(credentials, http).execute(
            ReadPublicationDetailsInputDTO(
                ResourceSettingsDTO(
                    "https://my.prom.ua", {"locales": ["ru"], "currency": "UAH"}
                ),
                "company:1000",
                "product",
                "102",
            )
        )
        self.assertEqual(
            [(image.id, image.url) for image in result.images],
            [
                ("main", "https://images.prom.ua/100_product.jpg"),
                ("200", "https://images.prom.ua/200_product_back.png"),
            ],
        )
        self.assertEqual(
            result.core.main_image_url, "https://images.prom.ua/100_product.jpg"
        )

    def test_other_urls_are_not_rewritten(self) -> None:
        """Не меняет чужой host, подпись, исходный файл или некорректный вход."""
        for value in (
            "https://images.prom.ua/100_product.jpg",
            "https://other.example/100_w200_h200_product.jpg",
            "https://images.prom.ua.other.example/100_w200_h200_product.jpg",
            "https://user:password@images.prom.ua/100_w200_h200_product.jpg",
            "http://images.prom.ua/100_w200_h200_product.jpg",
            "https://images.prom.ua:8443/100_w200_h200_product.jpg",
            "https://images.prom.ua/100_w200_h200_product.jpg?signature=test",
            "https://images.prom.ua/100_w200_h200_product.jpg#fragment",
            "https://images.prom.ua/product_w200_h200_product.jpg",
            "https://[invalid/100_w200_h200_product.jpg",
            None,
            100,
        ):
            with self.subTest(value=value):
                self.assertEqual(original_image_url(value), value)
