from copy import deepcopy
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET
from urllib.parse import urlsplit

from defusedxml.ElementTree import DefusedXMLParser
from defusedxml.common import DefusedXmlException
from pydantic import ValidationError

from src.modules.channels.application.content_feed.contracts import (
    MAX_FEED_BYTES,
    FeedOverlay,
    FeedStatistics,
    RenderedFeed,
)
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.channels.infrastructure.platforms.prom.feed_models import (
    PromFeedSettings,
)


class PromYmlSerializer:
    """Изменяет только контент исходных offer, сохраняя неизвестные расширения."""

    _content_tags = frozenset(
        {"name", "name_ua", "description", "description_ua", "picture"}
    )

    def validate_settings(self, source: FeedSourceVO) -> FeedSourceVO:
        """Отклоняет другой диалект и неоднозначный язык базовых тегов."""
        if source.schema != "prom.yml.v1":
            raise FeedBuildError("feed_format_unsupported")
        try:
            settings = PromFeedSettings.model_validate(source.settings)
        except ValidationError:
            raise FeedBuildError("feed_settings_invalid") from None
        return FeedSourceVO(source.schema, settings.model_dump(mode="json"))

    def render(
        self,
        *,
        source: bytes,
        settings: FeedSourceVO,
        overlays: tuple[FeedOverlay, ...],
    ) -> RenderedFeed:
        """Проверяет источник, все изменения и повторно разобранный готовый документ."""
        self.validate_settings(settings)
        original = self._parse(source)
        original_offers, categories = self._validate(original)
        result = deepcopy(original)
        offers = {
            offer.get("id"): offer for offer in result.findall("./shop/offers/offer")
        }
        used: set[str] = set()
        changed = 0
        for overlay in overlays:
            if not overlay.import_key or overlay.import_key in used:
                raise FeedBuildError(
                    "feed_import_key_duplicate", publication_id=overlay.publication_id
                )
            used.add(overlay.import_key)
            offer = offers.get(overlay.import_key)
            if offer is None:
                raise FeedBuildError(
                    "feed_offer_missing", publication_id=overlay.publication_id
                )
            before = ET.tostring(offer)
            self._overlay(offer, overlay)
            changed += ET.tostring(offer) != before
        if self._protected(original) != self._protected(result):
            raise FeedBuildError("feed_protected_fields_changed")
        content = ET.tostring(result, encoding="utf-8", xml_declaration=True)
        if len(content) > MAX_FEED_BYTES:
            raise FeedBuildError("feed_document_too_large")
        final_offers, final_categories = self._validate(self._parse(content))
        if set(original_offers) != set(final_offers) or categories != final_categories:
            raise FeedBuildError("feed_assortment_changed")
        return RenderedFeed(
            content, FeedStatistics(len(final_offers), changed, len(categories))
        )

    @staticmethod
    def _parse(source: bytes) -> ET.Element:
        """Допускает обычный DOCTYPE без загрузки DTD; запрещает любые entities."""
        if not source or len(source) > MAX_FEED_BYTES:
            raise FeedBuildError(
                "feed_document_too_large" if source else "feed_source_empty"
            )
        try:
            parser = DefusedXMLParser(
                target=ET.TreeBuilder(insert_comments=True, insert_pis=True),
                forbid_dtd=False,
                forbid_entities=True,
                forbid_external=True,
            )
            root = ET.fromstring(source, parser=parser)
        except (ET.ParseError, DefusedXmlException, ValueError):
            raise FeedBuildError("feed_xml_invalid") from None
        stack = [(root, 1)]
        nodes = 0
        while stack:
            node, depth = stack.pop()
            nodes += 1
            if depth > 128 or nodes > 200000:
                raise FeedBuildError("feed_xml_limits_exceeded")
            stack.extend((child, depth + 1) for child in node)
        return root

    @staticmethod
    def _validate(root: ET.Element) -> tuple[dict[str, ET.Element], dict[str, bytes]]:
        """Проверяет поддерживаемую структуру Prom, ключи, ссылки и обязательные поля."""
        if root.tag != "yml_catalog" or len(root.findall("shop")) != 1:
            raise FeedBuildError("feed_format_unsupported")
        shop = root.find("shop")
        assert shop is not None
        if len(shop.findall("offers")) != 1 or len(shop.findall("categories")) != 1:
            raise FeedBuildError("feed_structure_invalid")
        categories: dict[str, bytes] = {}
        parents: dict[str, str | None] = {}
        for node in shop.findall("./categories/category"):
            key = node.get("id", "")
            if not key.strip() or key in categories or not (node.text or "").strip():
                raise FeedBuildError("feed_category_invalid")
            categories[key] = ET.tostring(node)
            parents[key] = node.get("parentId")
        checked: set[str] = set()
        for key in parents:
            seen: set[str] = set()
            parent: str | None = key
            while parent is not None and parent not in checked:
                if parent not in parents or parent in seen:
                    raise FeedBuildError("feed_category_invalid")
                seen.add(parent)
                parent = parents[parent]
            checked.update(seen)
        offers: dict[str, ET.Element] = {}
        for node in shop.findall("./offers/offer"):
            key = node.get("id", "")
            if not key.strip():
                raise FeedBuildError("feed_import_key_missing")
            if key in offers:
                raise FeedBuildError("feed_import_key_duplicate")
            offers[key] = node
            if node.findtext("categoryId") not in categories:
                raise FeedBuildError("feed_category_missing")
            model = node.get("type") == "vendor.model"
            required = ("vendor", "model") if model else ("name",)
            if any(not (node.findtext(tag) or "").strip() for tag in required):
                raise FeedBuildError("feed_title_missing")
            if (
                node.find("name_ua") is not None
                or node.find("description_ua") is not None
            ):
                if not all(
                    (node.findtext(tag) or "").strip()
                    for tag in ("name_ua", "description_ua")
                ):
                    raise FeedBuildError("feed_uk_content_incomplete")
            if len(node.findall("picture")) > 10:
                raise FeedBuildError("feed_gallery_too_large")
            for picture in node.findall("picture"):
                try:
                    url = urlsplit(picture.text or "")
                    valid = (
                        url.scheme in {"http", "https"}
                        and bool(url.hostname)
                        and not url.username
                        and not url.password
                    )
                except ValueError:
                    valid = False
                if not valid:
                    raise FeedBuildError("feed_picture_invalid")
            for tag in ("price", "oldprice", "price_old", "old_price"):
                value = node.findtext(tag)
                if value is not None:
                    try:
                        number = Decimal(value)
                        if not number.is_finite() or number <= 0 or number > 9999999999:
                            raise InvalidOperation
                    except InvalidOperation:
                        raise FeedBuildError("feed_price_invalid") from None
            if (
                any(
                    node.find(tag) is not None
                    for tag in ("oldprice", "price_old", "old_price", "discount")
                )
                and node.find("price") is None
            ):
                raise FeedBuildError("feed_price_missing")
        if not offers:
            raise FeedBuildError("feed_source_empty")
        return offers, categories

    def _overlay(self, offer: ET.Element, overlay: FeedOverlay) -> None:
        """Не меняет модель названия или структуру вариантов ради применения контента."""
        for content in overlay.target.content:
            if content.locale not in {"ru", "uk"}:
                raise FeedBuildError(
                    "feed_locale_unsupported", publication_id=overlay.publication_id
                )
            suffix = "_ua" if content.locale == "uk" else ""
            if content.title is not None:
                if offer.get("type") == "vendor.model":
                    raise FeedBuildError(
                        "feed_vendor_model_title_unsupported",
                        publication_id=overlay.publication_id,
                        field="title",
                    )
                if not content.title.strip():
                    raise FeedBuildError(
                        "feed_title_missing",
                        publication_id=overlay.publication_id,
                        field="title",
                    )
                self._replace(offer, "name" + suffix, (content.title,))
            if content.body is not None:
                if content.body == "":
                    raise FeedBuildError(
                        "feed_description_clear_unsupported",
                        publication_id=overlay.publication_id,
                        field="body",
                    )
                self._replace(offer, "description" + suffix, (content.body,))
        if overlay.gallery is not None:
            if not overlay.gallery:
                raise FeedBuildError(
                    "feed_gallery_clear_unsupported",
                    publication_id=overlay.publication_id,
                    field="gallery",
                )
            if len(overlay.gallery) > 10:
                raise FeedBuildError(
                    "feed_gallery_too_large",
                    publication_id=overlay.publication_id,
                    field="gallery",
                )
            self._replace(offer, "picture", overlay.gallery)

    @staticmethod
    def _replace(offer: ET.Element, tag: str, values: tuple[str, ...]) -> None:
        """Заменяет только выбранные элементы в месте первого исходного элемента."""
        children = list(offer)
        selected = [node for node in children if node.tag == tag]
        index = children.index(selected[0]) if selected else len(children)
        for node in selected:
            offer.remove(node)
        for offset, value in enumerate(values):
            node = ET.Element(tag)
            node.text = value
            offer.insert(index + offset, node)

    def _protected(self, root: ET.Element) -> bytes:
        """Сравнивает все поля за пределами разрешённого контента, включая расширения."""
        value = deepcopy(root)
        for offer in value.findall("./shop/offers/offer"):
            for node in list(offer):
                if node.tag in self._content_tags:
                    offer.remove(node)
        return ET.tostring(value)
