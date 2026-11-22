"""Рабочая схема Feed: Domain, сценарии и закрытые HTTP-контракты."""

import copy
from dataclasses import replace
from datetime import timedelta
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from pydantic import ValidationError
from test.test_feed_builder_domain import feed, NOW
from test.test_feed_builder_crud import rich_feed
from src.modules.feed_builder.application.feed.schema_definition import decode_schema
from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.application.feed.schema_error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.command import (
    SaveFeedSchemaDraftCommand,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.handler import (
    SaveFeedSchemaDraftHandler,
)
from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocaleDTO,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedDomainError,
    FeedArchivedError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.presentation.feed.http.request.put_feed_schema import (
    PutFeedSchemaRequest,
)
from src.modules.feed_builder.presentation.feed.http.schema.definition import (
    SchemaDefinition,
)
from src.modules.feed_builder.presentation.feed.http.schema.body_limit import (
    excessive_json_depth,
)


def source_schema_document() -> dict:
    """Возвращает четыре равноправных поля с прямыми источниками и точными настройками."""
    result = schema_document(rich_feed().schema)
    for field, path in zip(
        result["root"]["fields"],
        ["item.title", "item.description", "item.sku", "item.regular_price"],
    ):
        t = field["type_definition"]
        t["value"] = (
            {"kind": "MONEY", "mode": "SOURCE"}
            if t["kind"] == "money"
            else {"kind": "SOURCE"}
        ) | {"source": {"provider": "catalog", "path": path}}
        if path in ("item.title", "item.description"):
            t["locale"] = "uk"
    result["root"]["fields"][-1]["type_definition"]["constraints"][
        "min_amount"
    ] = "1E-18"
    return result


class FeedSchemaDomainTests(TestCase):
    """Проверяет атомарную замену и неизменность исходного frozen-корня."""

    def test_change_noop_order_identity_and_empty(self) -> None:
        """Сохраняет ID, даты, настройки, порядок и версию реального изменения."""
        original = feed()
        schema = decode_schema(source_schema_document())
        saved = original.change_schema(schema=schema, now=NOW + timedelta(seconds=1))
        self.assertEqual(saved.version.value, 2)
        self.assertEqual(saved.id, original.id)
        self.assertEqual(saved.export_settings, original.export_settings)
        self.assertEqual(saved.created_at, original.created_at)
        self.assertEqual(original.schema.fields, ())
        self.assertIs(
            saved.change_schema(schema=schema, now=NOW + timedelta(seconds=2)), saved
        )
        reversed_schema = FeedSchemaVO(tuple(reversed(schema.fields)))
        reordered = saved.change_schema(
            schema=reversed_schema, now=NOW + timedelta(seconds=2)
        )
        self.assertEqual(
            [f.id for f in reordered.schema.fields],
            [f.id for f in reversed_schema.fields],
        )
        self.assertEqual(
            reordered.change_schema(
                schema=FeedSchemaVO(), now=NOW + timedelta(seconds=3)
            ).schema.fields,
            (),
        )

    def test_invalid_schema_and_archive_never_partially_change_root(self) -> None:
        """Отклоняет дубликаты, несовместимые источники, язык SKU и отсутствие локали."""
        original = feed()
        document = source_schema_document()
        invalid = []
        for key in ("id", "key"):
            value = copy.deepcopy(document)
            value["root"]["fields"][1][key] = value["root"]["fields"][0][key]
            invalid.append(value)
        value = copy.deepcopy(document)
        value["root"]["fields"][1]["export"]["name"] = value["root"]["fields"][0][
            "export"
        ]["name"]
        invalid.append(value)
        value = copy.deepcopy(document)
        value["root"]["fields"][0]["type_definition"]["value"]["source"][
            "path"
        ] = "item.regular_price"
        invalid.append(value)
        value = copy.deepcopy(document)
        value["root"]["fields"][0]["type_definition"]["locale"] = None
        invalid.append(value)
        value = copy.deepcopy(document)
        value["root"]["fields"][2]["type_definition"]["locale"] = "uk"
        invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(FeedDomainError):
                original.change_schema(schema=decode_schema(value), now=NOW)
            self.assertEqual(original.schema.fields, ())
        with self.assertRaises(FeedArchivedError):
            original.archive(now=NOW).change_schema(
                schema=decode_schema(document), now=NOW
            )
        with self.assertRaises(FeedDomainError):
            original.change_schema(
                schema=decode_schema(document), now=NOW - timedelta(seconds=1)
            )

    def test_typed_http_ast_roundtrip_has_no_injected_null_properties(self) -> None:
        """Сохраняет все известные узлы, AI, Decimal-строки, transforms и nullable currency."""
        for source in (schema_document(rich_feed().schema), source_schema_document()):
            schema = SchemaDefinition.model_validate(source)
            wire = schema.model_dump(mode="json", exclude_unset=True)
            self.assertEqual(wire, source)
            self.assertEqual(schema_document(decode_schema(wire)), source)

    def test_http_rejects_unknown_shapes_cross_type_settings_and_limits(self) -> None:
        """Отклоняет прямые обходы UI, старые aliases, неточные суммы и чужие свойства."""
        document = source_schema_document()
        for target, key, value in [
            ("type_definition", "currency", "USD"),
            ("field", "locale", "uk"),
            ("source", "path", "item.arbitrary"),
            ("type_definition", "value_type", "STRING"),
        ]:
            source = copy.deepcopy(document)
            field = source["root"]["fields"][0]
            item = (
                field
                if target == "field"
                else (
                    field["type_definition"]["value"]["source"]
                    if target == "source"
                    else field["type_definition"]
                )
            )
            item[key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                PutFeedSchemaRequest.model_validate(
                    {"expected_version": 1, "definition": source}
                )
        value = copy.deepcopy(document)
        value["root"]["fields"][-1]["type_definition"]["constraints"][
            "min_amount"
        ] = 0.1
        with self.assertRaises(ValidationError):
            SchemaDefinition.model_validate(value)
        for version in (None, 0, True, "1"):
            with self.assertRaises(ValidationError):
                PutFeedSchemaRequest.model_validate(
                    {"expected_version": version, "definition": document}
                )
        with self.assertRaises((InvalidFeedSchemaDocumentError, FeedDomainError)):
            decode_schema(
                {
                    "schema_format_version": 1,
                    "root": {
                        "key": "publication",
                        "kind": "object",
                        "fields": [document["root"]["fields"][0]] * 201,
                    },
                }
            )
        self.assertTrue(excessive_json_depth(b"[" * 200 + b"0" + b"]" * 200))
        self.assertFalse(excessive_json_depth(b'{"text":"' + b"[" * 200 + b'"}'))


class FeedSchemaApplicationTests(IsolatedAsyncioTestCase):
    """Проверяет версию, locale port и сохранение после чистой проверки Domain."""

    async def asyncSetUp(self) -> None:
        """Собирает сценарий без инфраструктуры."""
        self.original = feed()
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.original), save=AsyncMock()
        )
        self.locales = Mock(
            list_available=AsyncMock(
                return_value=(
                    SchemaLocaleDTO("uk", "Українська"),
                    SchemaLocaleDTO("ru", "Русский"),
                )
            )
        )
        self.handler = SaveFeedSchemaDraftHandler(
            self.repository, self.locales, Mock(now=lambda: NOW)
        )

    async def test_save_and_noop_use_one_snapshot_and_one_locale_lookup(self) -> None:
        """Записывает через корень и не обновляет версию неизменённого определения."""
        command = SaveFeedSchemaDraftCommand(
            self.original.id, 1, source_schema_document()
        )
        result = await self.handler.execute(command)
        self.assertEqual(result.version, 2)
        self.locales.list_available.assert_awaited_once()
        saved = self.repository.save.call_args.args[0]
        self.repository.get_for_update.return_value = saved
        self.repository.save.reset_mock()
        same = await self.handler.execute(
            replace(command, expected_version=2, definition=result.definition)
        )
        self.assertEqual(same.version, 2)
        self.repository.save.assert_not_awaited()

    async def test_conflict_archive_and_unavailable_locale_do_not_write(self) -> None:
        """Ожидаемые отказы оставляют хранилище и исходный агрегат нетронутыми."""
        document = source_schema_document()
        with self.assertRaises(FeedVersionConflictError):
            await self.handler.execute(
                SaveFeedSchemaDraftCommand(self.original.id, 2, document)
            )
        self.locales.list_available.assert_not_awaited()
        self.locales.list_available.return_value = ()
        with self.assertRaises(FeedDomainError):
            await self.handler.execute(
                SaveFeedSchemaDraftCommand(self.original.id, 1, document)
            )
        self.repository.get_for_update.return_value = self.original.archive(now=NOW)
        with self.assertRaises(FeedArchivedError):
            await self.handler.execute(
                SaveFeedSchemaDraftCommand(self.original.id, 2, document)
            )
        self.repository.save.assert_not_awaited()
