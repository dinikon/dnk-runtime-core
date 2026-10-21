from decimal import Decimal
import re
from typing import BinaryIO
from urllib.parse import quote, urlsplit
from xml.sax.saxutils import escape, quoteattr
from src.modules.channels.application.batch_export.plugin_contract import (
    ExportInspectionDTO,
    ExportIdentityDTO,
    ExportIdentityPageDTO,
    ExportPollDTO,
)
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ProviderJsonValue,
)
from src.modules.channels.application.port.plugin_services import (
    PluginCredentialsAccess,
    PluginBatchHttpTransport,
    PluginCallError,
)
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO
from src.modules.channels.domain.external_publication.value_object.core import JsonValue
from src.modules.channels.infrastructure.plugin.prom.manifest import PromSettings
from src.modules.channels.infrastructure.plugin.prom.translations import localized_field
from src.modules.channels.infrastructure.plugin.content_normalizer import content_body

PRESERVED = (
    "sku",
    "price",
    "prices",
    "discount",
    "currency",
    "quantity_in_stock",
    "quantity",
    "presence",
    "presence_sure",
    "status",
    "group",
    "category",
    "main_image",
    "images",
    "minimum_order_quantity",
    "measure",
    "measure_unit",
    "selling_type",
    "keywords",
    "attributes",
    "is_variation",
    "variation_base_id",
    "variation_group_id",
    "variation_modifications",
)


def json_value(value: ProviderJsonValue) -> JsonValue:
    """Сохраняет сравнимые значения API без потери точности decimal."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_value(item) for item in value]
    return value


def baseline(row: dict[str, ProviderJsonValue]) -> dict[str, JsonValue]:
    """Выделяет только поля, сохранение которых проверяет этот контракт."""
    result = {key: json_value(row.get(key)) for key in PRESERVED}
    result["native_id"], result["import_key"] = str(row.get("id")), row.get(
        "external_id"
    )
    return result


def xml_text(value: str) -> str:
    """Отклоняет недопустимые XML 1.0 символы вместо тихой потери текста."""
    if any(
        not (
            c in "\t\n\r"
            or "\u0020" <= c <= "\ud7ff"
            or "\ue000" <= c <= "\ufffd"
            or "\U00010000" <= c <= "\U0010ffff"
        )
        for c in value
    ):
        raise PluginCallError("invalid_xml_character")
    return escape(value)


class PromBatchExportPlugin:
    """Владеет XML Prom, ключами файла и четырьмя разрешёнными полями импорта."""

    def __init__(
        self, credentials: PluginCredentialsAccess, http: PluginBatchHttpTransport
    ) -> None:
        """Принимает только scoped фасады без доступа к SQL и каталогу."""
        self.credentials, self.http = credentials, http

    async def headers(self) -> dict[str, str]:
        """Получает секрет только перед сетевым шагом без сохранения в снимке."""
        return {
            "Authorization": "Bearer "
            + (await self.credentials.resolve()).values["token"],
            "X-LANGUAGE": "ru",
        }

    async def product(self, identifier: str) -> dict[str, ProviderJsonValue]:
        """Читает исходный native ID и отвергает подмену карточки."""
        if not identifier.isdecimal():
            raise PluginCallError("unsupported_publication_type")
        response = await self.http.get(
            "/api/v1/products/" + identifier, headers=await self.headers()
        )
        row = response.body.get("product") if isinstance(response.body, dict) else None
        if not isinstance(row, dict) or str(row.get("id")) != identifier:
            raise PluginCallError("invalid_publication_identity")
        return row

    async def inspect(
        self, settings: ResourceSettingsDTO, item: ExportItemVO
    ) -> ExportInspectionDTO:
        """Допускает опубликованный простой товар с существующим ключом и категорией."""
        PromSettings.model_validate(settings.options)
        row = await self.product(item.external_id)
        key = row.get("external_id")
        issues = []
        if not isinstance(key, str) or not key.strip() or len(key) > 512:
            key = None
            issues.append("export_identity_missing")
        expected = item.provider_context.get("import_key")
        if key is not None and key != expected:
            issues.append("export_identity_changed")
        if row.get("status") != "on_display":
            issues.append("export_visibility_unsupported")
        if row.get("is_variation") is True:
            issues.append("export_variation_unsupported")
        category = row.get("category")
        if not isinstance(category, dict) or type(category.get("id")) is not int:
            issues.append("export_category_missing")
        return ExportInspectionDTO(key, baseline(row), tuple(issues))

    async def identities(
        self, settings: ResourceSettingsDTO, cursor: str | None
    ) -> ExportIdentityPageDTO:
        """Обходит весь кабинет по native ID, включая не входящие в пакет публикации."""
        query = {"limit": "100"}
        if cursor is not None:
            if not cursor.isdecimal():
                raise PluginCallError("invalid_export_cursor")
            query["last_id"] = cursor
        response = await self.http.get(
            "/api/v1/products/list", query=query, headers=await self.headers()
        )
        rows = (
            response.body.get("products") if isinstance(response.body, dict) else None
        )
        if not isinstance(rows, list) or len(rows) > 100:
            raise PluginCallError("invalid_provider_response")
        values = []
        for row in rows:
            if (
                not isinstance(row, dict)
                or type(row.get("id")) is not int
                or row["id"] <= 0
            ):
                raise PluginCallError("invalid_publication_identity")
            identifier = row["id"]
            if cursor is not None and identifier > int(cursor):
                raise PluginCallError("cursor_did_not_advance")
            key = row.get("external_id")
            if key is not None and not isinstance(key, str):
                raise PluginCallError("invalid_publication_identity")
            values.append(ExportIdentityDTO(str(identifier), key, baseline(row)))
        return ExportIdentityPageDTO(
            tuple(values),
            str(min(int(v.external_id) for v in values) - 1) if values else None,
            not values,
        )

    def begin(self, target: BinaryIO) -> None:
        """Открывает минимальный XML без цен, остатков и управления отсутствующими товарами."""
        target.write(
            b'<?xml version="1.0" encoding="UTF-8"?>\n<yml_catalog><shop><name>Catalog</name><offers>\n'
        )

    def append(self, target: BinaryIO, item: ExportItemVO) -> None:
        """Передаёт текущую категорию явно для защиты от автокатегоризации Prom."""
        if (
            not item.identity_key
            or item.desired is None
            or item.baseline is None
            or item.desired.missing_content()
        ):
            raise PluginCallError("invalid_export_snapshot")
        category = item.baseline.get("category")
        if not isinstance(category, dict) or type(category.get("id")) is not int:
            raise PluginCallError("export_category_missing")
        xml_text(item.identity_key)
        rows = ["<offer id=" + quoteattr(item.identity_key) + ">"]
        for text in item.desired.translations:
            suffix = {"ru": "", "uk": "_ua"}.get(text.locale)
            if suffix is None:
                raise PluginCallError("unsupported_export_locale")
            rows.extend(
                [
                    "<name"
                    + suffix
                    + ">"
                    + xml_text(text.title or "")
                    + "</name"
                    + suffix
                    + ">",
                    "<description"
                    + suffix
                    + ">"
                    + xml_text(text.body or "")
                    + "</description"
                    + suffix
                    + ">",
                ]
            )
        rows.append(
            "<portal_category_id>"
            + str(category["id"])
            + "</portal_category_id></offer>\n"
        )
        target.write("".join(rows).encode())

    def end(self, target: BinaryIO) -> None:
        """Завершает документ без управляющих карточками тегов."""
        target.write(b"</offers></shop></yml_catalog>\n")

    async def submit(self, settings: ResourceSettingsDTO, url: str) -> str:
        """Отправляет только тексты и запрещает изменение отсутствующих в файле карточек."""
        config = PromSettings.model_validate(settings.options)
        try:
            parsed = urlsplit(url)
            safe = (
                parsed.scheme == "https"
                and parsed.hostname
                and not parsed.username
                and not parsed.password
            )
        except ValueError:
            safe = False
        if not safe or len(url) > 1024:
            raise PluginCallError("invalid_export_payload")
        fields = ["name", "description"]
        if "uk" in config.locales:
            fields += ["name_ua", "description_ua"]
        response = await self.http.post(
            "/api/v1/products/import_url",
            payload={
                "url": url,
                "force_update": True,
                "only_available": False,
                "mark_missing_product_as": "none",
                "updated_fields": fields,
            },
            headers=await self.headers(),
        )
        value = response.body
        if (
            not isinstance(value, dict)
            or value.get("status") != "success"
            or not isinstance(value.get("id"), str)
            or not re.fullmatch("[a-zA-Z0-9_-]{1,200}", value["id"])
        ):
            raise PluginCallError("invalid_provider_response")
        return value["id"]

    async def poll(self, remote_id: str) -> ExportPollDTO:
        """Нулевые счётчики не подтверждают завершение; запись доказывает verify."""
        if not re.fullmatch("[a-zA-Z0-9_-]{1,200}", remote_id):
            raise PluginCallError("invalid_export_remote_id")
        response = await self.http.get(
            "/api/v1/products/import/status/" + quote(remote_id, safe=""),
            headers=await self.headers(),
        )
        value = response.body
        if not isinstance(value, dict):
            raise PluginCallError("invalid_provider_response")
        total = value.get("total")
        failed = value.get("status") == "FATAL"
        return ExportPollDTO(
            failed
            or (
                value.get("status") in ("SUCCESS", "PARTIAL")
                and isinstance(total, int)
                and total > 0
            ),
            failed,
        )

    async def verify(
        self, settings: ResourceSettingsDTO, item: ExportItemVO
    ) -> tuple[str, ...]:
        """Сверяет четыре текста и поля исходного товара, не доверяя счётчику updated."""
        row = await self.product(item.external_id)
        issues = []
        if baseline(row) != item.baseline:
            issues.append("export_preserved_fields_changed")
        if item.desired is None:
            raise PluginCallError("invalid_export_snapshot")
        for text in item.desired.translations:
            if localized_field(row, "name", text.locale) != text.title or content_body(
                localized_field(row, "description", text.locale)
            ) != content_body(text.body):
                issues.append("export_texts_not_confirmed")
        return tuple(dict.fromkeys(issues))
