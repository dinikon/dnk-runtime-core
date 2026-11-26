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
from src.modules.feed_builder.application.feed.graph.codec import decode_schema
from src.modules.feed_builder.application.feed.graph.codec import schema_document
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.command import (
    SaveFeedSchemaDraftCommand,
)
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.handler import (
    SaveFeedSchemaDraftHandler,
)
from src.modules.feed_builder.domain.feed.error import (
    FeedDomainError,
    FeedArchivedError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.presentation.feed.http.request.put_feed_schema import (
    PutFeedSchemaRequest,
)
from src.modules.feed_builder.presentation.feed.http.schema.legacy_graph import (
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

    def test_category_field_preserves_ids_and_rejects_cycles(self) -> None:
        """Читает старый документ как поле и сохраняет идентичность его записей."""
        first, second, third = map(str, (uuid4(), uuid4(), uuid4()))
        old = source_schema_document()
        old["categories"] = {
            "version": 1,
            "enabled": True,
            "profile": "GENERIC",
            "locale": "ru",
            "nodes": [
                {"id": first, "name": "Родитель", "export_id": "1"},
                {
                    "id": second,
                    "name": "Дочерняя",
                    "parent_id": first,
                    "export_id": "2",
                },
            ],
            "rules": [],
            "fallback": "NONE",
        }
        with self.assertRaises(ValidationError):
            SchemaDefinition.model_validate(old)
        previous = decode_schema(old)
        document = schema_document(previous)
        self.assertNotIn("categories", document)
        self.assertEqual(schema_document(decode_schema(document)), document)
        value = document["root"]["fields"][-1]["type_definition"]["value"]
        value["nodes"] = [
            {"id": first, "values": {"name": "Переименована"}},
            {"id": third, "values": {"name": "Новая"}},
        ]
        changed = schema_document(decode_schema(document, previous_schema=previous))
        nodes = changed["root"]["fields"][-1]["type_definition"]["value"]["nodes"]
        self.assertEqual([node["values"]["id"] for node in nodes], ["1", "3"])
        value["nodes"][0]["values"]["id"] = "9"
        with self.assertRaises(InvalidFeedSchemaDocumentError):
            decode_schema(document, previous_schema=previous)
        value["nodes"][0]["values"].pop("id")
        value["nodes"][0]["parent_id"] = third
        value["nodes"][1]["parent_id"] = first
        with self.assertRaises(FeedDomainError):
            decode_schema(document)

    def test_v2_category_nodes_reference_one_feed_tree(self) -> None:
        """Хранит дерево отдельно, связывает его с нодой и сохраняет экспортный ID."""
        legacy = source_schema_document()
        legacy["categories"] = {
            "version": 1,
            "enabled": True,
            "profile": "GENERIC",
            "locale": "ru",
            "nodes": [{"id": str(uuid4()), "name": "Аудио", "export_id": "100"}],
            "rules": [],
            "fallback": "NONE",
        }
        inline = schema_document(decode_schema(legacy))["root"]["fields"][-1]
        settings = dict(inline["type_definition"])
        settings.pop("kind")
        graph = {
            "schema_format_version": 2,
            "fields": [{
                "id": inline["id"], "key": inline["key"], "name": inline["label"],
                "typeId": "core.category_reference", "typeVersion": 1, "scope": "offer",
                "data": {"source": "feed", "treeId": inline["id"]},
                "export": inline["export"],
            }],
            "categoryTrees": [{"id": inline["id"], "data": settings}],
        }
        saved = feed().change_schema(schema=decode_schema(graph), now=NOW)
        self.assertEqual(saved.schema.fields[0].category_tree_id, saved.schema.category_trees[0].id)
        wire = schema_document(saved.schema)
        self.assertEqual(wire["fields"][0]["data"], graph["fields"][0]["data"])
        self.assertEqual(wire["categoryTrees"][0]["data"]["value"]["nodes"][0]["values"]["id"], "100")
        self.assertEqual(schema_document(decode_schema(wire)), wire)
        graph["categoryTrees"] = []
        with self.assertRaises(InvalidFeedSchemaDocumentError):
            decode_schema(graph)

    def test_legacy_category_property_preserves_shared_xml_names(self) -> None:
        """Сохраняет значения одноимённых атрибута и тега прежнего блока."""
        definition = source_schema_document()
        definition["categories"] = {
            "version": 1,
            "enabled": True,
            "profile": "GENERIC",
            "locale": "ru",
            "attribute_types": {"code": "string"},
            "element_types": {"code": "number"},
            "nodes": [
                {
                    "id": str(uuid4()),
                    "name": "Расходные материалы",
                    "export_id": "1",
                    "attributes": {"code": "WH-01"},
                    "elements": {"code": 0},
                }
            ],
            "rules": [],
            "fallback": "NONE",
        }
        canonical = schema_document(decode_schema(definition))
        SchemaDefinition.model_validate(canonical)
        category = canonical["root"]["fields"][-1]["type_definition"]
        values = category["value"]["nodes"][0]["values"]
        codes = {
            prop["xml"]["placement"]: values[prop["key"]]
            for prop in category["object_schema"]["fields"]
            if prop["xml"]["name"] == "code"
        }
        self.assertEqual(codes, {"ATTRIBUTE": "WH-01", "ELEMENT": 0})

    def test_text_constant_obeys_character_and_length_constraints(self) -> None:
        """Отличает недопустимый текст константы от обычной ошибки источника."""
        definition = source_schema_document()
        settings = definition["root"]["fields"][0]["type_definition"]
        settings.update(
            locale=None,
            fallback_policy=None,
            transforms=[],
            constraints={"required": True, "min_length": 1, "max_length": 3},
        )
        for value in ("    ", "r\n", "too long", "\x00"):
            with self.subTest(value=value):
                settings["value"] = {"kind": "CONSTANT", "value": value}
                with self.assertRaises(FeedDomainError) as error:
                    decode_schema(definition)
                self.assertEqual(
                    error.exception.path[-3:], ("type_definition", "value", "value")
                )
        settings["value"] = {"kind": "CONSTANT", "value": False}
        with self.assertRaises(ValidationError):
            SchemaDefinition.model_validate(definition)

    def test_xml_attribute_roundtrip_and_reserved_name(self) -> None:
        """Читает старое размещение и сохраняет выбор атрибута с проверкой имени."""
        definition = source_schema_document()
        self.assertIs(
            decode_schema(definition).fields[0].export.xml_placement,
            XmlFieldPlacement.ELEMENT,
        )
        export = definition["root"]["fields"][0]["export"]
        export.update(name="id", xml_placement="ATTRIBUTE")
        wire = SchemaDefinition.model_validate(definition).model_dump(
            mode="json", exclude_unset=True
        )
        self.assertEqual(schema_document(decode_schema(wire)), definition)

        export["name"] = "xmlns"
        with self.assertRaises(FeedDomainError) as error:
            decode_schema(definition)
        self.assertEqual(
            error.exception.path, ("definition", "root", "fields", 0, "export", "name")
        )
        export["xml_placement"] = True
        with self.assertRaises(ValidationError):
            SchemaDefinition.model_validate(definition)

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
                SchemaDefinition.model_validate(source)
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

    def test_save_request_clears_fields_before_nested_validation(self) -> None:
        """Произвольный вход полей заменяется пустым списком без изменения запроса."""
        document = source_schema_document()
        for fields in (
            document["root"]["fields"],
            [{"kind": "unknown"}],
            {},
            None,
            42,
            "text",
            False,
        ):
            with self.subTest(fields=fields):
                definition = {
                    **document,
                    "root": {**document["root"], "fields": fields},
                }
                payload = PutFeedSchemaRequest.model_validate(
                    {"expected_version": 1, "definition": definition}
                )
                self.assertEqual(payload.definition.root.fields, [])
                self.assertIs(definition["root"]["fields"], fields)
        definition = {**document, "root": {"key": "publication", "kind": "object"}}
        self.assertEqual(
            PutFeedSchemaRequest.model_validate(
                {"expected_version": 1, "definition": definition}
            ).definition.root.fields,
            [],
        )


class FeedSchemaApplicationTests(IsolatedAsyncioTestCase):
    """Проверяет очистку схемы, ожидаемую версию и правила записи."""

    async def asyncSetUp(self) -> None:
        """Собирает сценарий без инфраструктуры."""
        self.original = rich_feed()
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.original), save=AsyncMock()
        )
        self.handler = SaveFeedSchemaDraftHandler(
            self.repository, Mock(now=lambda: NOW), AsyncMock()
        )

    async def test_save_clears_fields_once(self) -> None:
        """Очищает старые поля через корень и сохраняет версию при повторе."""
        command = SaveFeedSchemaDraftCommand(self.original.id, 1)
        result = await self.handler.execute(command)
        self.assertEqual(result.version, 2)
        self.assertEqual(result.definition["root"]["fields"], [])
        saved = self.repository.save.call_args.args[0]
        self.assertEqual(saved.schema.fields, ())
        self.assertEqual(saved.export_settings, self.original.export_settings)
        self.repository.get_for_update.return_value = saved
        self.repository.save.reset_mock()
        same = await self.handler.execute(replace(command, expected_version=2))
        self.assertEqual(same.version, 2)
        self.repository.save.assert_not_awaited()

    async def test_conflict_and_archive_do_not_write(self) -> None:
        """Ожидаемые отказы оставляют хранилище и исходный агрегат нетронутыми."""
        with self.assertRaises(FeedVersionConflictError):
            await self.handler.execute(SaveFeedSchemaDraftCommand(self.original.id, 2))
        self.repository.get_for_update.return_value = self.original.archive(now=NOW)
        with self.assertRaises(FeedArchivedError):
            await self.handler.execute(SaveFeedSchemaDraftCommand(self.original.id, 2))
        self.repository.save.assert_not_awaited()
