from datetime import UTC, datetime, timedelta

"""Проверяемые wire-ответы внешних API и изображения для полного импорта."""

import base64
from src.modules.channels.application.plugin_contract import HttpResultDTO
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.application.publication_import.port.images import (
    DownloadedPublicationImageDTO,
)
from test.test_channels_postgres import StoreFixtureTransport

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
)


class FullPublicationTransport(StoreFixtureTransport):
    """Дополняет штатную paginated fixture отдельным GET карточки."""

    async def get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Возвращает реальные multilang поля Prom независимо от X-LANGUAGE."""
        if path.startswith("/api/v1/products/") and path.rsplit("/", 1)[-1].isdecimal():
            self.calls.append((path, dict(query or {})))
            if self.denied:
                raise PluginCallError("permission_denied")
            return HttpResultDTO(
                {
                    "product": {
                        "id": int(path.rsplit("/", 1)[-1]),
                        "sku": "PROM-IMPORT",
                        "name": "Название с Prom",
                        "name_multilang": {
                            "ru": "Название с Prom",
                            "uk": "Назва з Prom",
                        },
                        "description": "<p>Описание по-русски</p>",
                        "description_multilang": {
                            "ru": "<p>Описание по-русски</p>",
                            "uk": "<p>Опис українською</p>",
                        },
                        "price": "120.50",
                        "discount": {
                            "type": "amount",
                            "value": 20,
                            "date_start": (
                                datetime.now(UTC) - timedelta(days=7)
                            ).strftime("%d.%m.%Y"),
                            "date_end": (
                                datetime.now(UTC) + timedelta(days=7)
                            ).strftime("%d.%m.%Y"),
                        },
                        "currency": "UAH",
                        "presence": "available",
                        "main_image": "https://images.example/1.png",
                        "images": [
                            {"id": 100, "url": "https://images.example/1.png"},
                            {"id": 200, "url": "https://images.example/2.png"},
                        ],
                    }
                },
                {},
            )
        if (
            path.startswith("/wp-json/wc/v3/products/")
            and path.rsplit("/", 1)[-1].isdecimal()
        ):
            self.calls.append((path, dict(query or {})))
            if self.denied:
                raise PluginCallError("permission_denied")
            identifier = int(path.rsplit("/", 1)[-1])
            if "/variations/" in path:
                return HttpResultDTO(
                    {
                        "id": identifier,
                        "sku": "VAR-FULL",
                        "description": "",
                        "image": None,
                        "regular_price": "90",
                        "stock_status": "instock",
                    },
                    {},
                )
            return HttpResultDTO(
                {
                    "id": identifier,
                    "name": "Повна картка Woo",
                    "sku": "WOO-IMPORT",
                    "description": "<script>bad()</script><p>Опис <strong>товару</strong></p>",
                    "regular_price": "123.45",
                    "sale_price": "100",
                    "stock_quantity": 8,
                    "stock_status": "outofstock",
                    "images": [
                        {
                            "id": 1,
                            "src": "https://images.example/1.png",
                            "alt": "Головне фото",
                        },
                        {
                            "id": 2,
                            "src": "https://images.example/2.png",
                            "alt": "Друге фото",
                        },
                    ],
                },
                {},
            )
        return await super().get(path, query=query, headers=headers)


class FixtureImageDownloader:
    """Возвращает настоящее PNG содержимое без сетевого запроса к внешнему CDN."""

    def __init__(self) -> None:
        """Запоминает обращения и позволяет воспроизвести частичный сбой."""
        self.calls: list[str] = []
        self.fail_second = False

    async def download(self, url: str) -> DownloadedPublicationImageDTO:
        """Эмулирует отказ одной фотографии, сохраняя внешний контракт загрузки."""
        self.calls.append(url)
        if self.fail_second and url.endswith("2.png"):
            raise PluginCallError("image_network_error", retryable=True)
        return DownloadedPublicationImageDTO(PNG, "image/png")
