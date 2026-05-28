from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
    RuntimeRelationDescriptor,
)
from src.modules.segmentation.application.segment_version.dsl import (
    SegmentVersionDslConfigValidator,
    SegmentVersionDslInvalidContactMappingError,
    SegmentVersionDslInvalidInheritedSegmentError,
    SegmentVersionDslInvalidRelationPathError,
    SegmentVersionDslInvalidRootObjectError,
    SegmentVersionDslInvalidRuleError,
    SegmentVersionDslParseError,
    SegmentVersionDslRuleLimitError,
    SegmentVersionDslValidationError,
    dump_segment_version_dsl_config,
    parse_segment_version_dsl_config,
)
from src.modules.segmentation.application.segment_version.query import (
    SegmentVersionRuntimeRelationMetadata,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinition,
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)
from src.modules.segmentation.infrastructure import (
    RuntimeFilterValidatorAdapter,
    RuntimeObjectMetadataAdapter,
)
from src.modules.shared import EntityIdVO


def _field(name: str, type_code: str = "text") -> RuntimeFieldDescriptor:
    return RuntimeFieldDescriptor(
        name=name,
        type_code=type_code,
        is_nullable=False,
        default_value=None,
        options={},
        settings={},
    )


def _relation(
    *,
    source_object: str = "loan_applications",
    target_object: str = "contacts",
    source_relation_name: str = "contact",
    target_relation_name: str = "loan_applications",
    fk_field: str | None = "contact_id",
) -> RuntimeRelationDescriptor:
    return RuntimeRelationDescriptor(
        id=str(uuid4()),
        name="loan_application_contact",
        label=None,
        relation_type="many_to_one",
        source_object=source_object,
        target_object=target_object,
        source_relation_name=source_relation_name,
        target_relation_name=target_relation_name,
        owning_object=source_object,
        fk_field=fk_field,
        referenced_object=target_object,
        referenced_field="id",
        relation_table_name=None,
        source_join_column_name=None,
        target_join_column_name=None,
        on_delete="restrict",
        is_required=False,
        is_collection=False,
        is_virtual=False,
        is_unique=False,
        kind="standard",
        settings={},
    )


def _descriptor(
    object_name: str,
    *,
    table_name: str | None = None,
    fields: tuple[RuntimeFieldDescriptor, ...] | None = None,
    relations: tuple[RuntimeRelationDescriptor, ...] = (),
) -> RuntimeObjectDescriptor:
    return RuntimeObjectDescriptor(
        schema_name="dnk_test",
        object_name=object_name,
        table_name=table_name or f"{object_name}s",
        pk="id",
        title_field="id",
        fields=fields or (_field("id", "uuid"),),
        relations=relations,
    )


def _contact_config() -> dict:
    return {
        "root_object": "contact",
        "include": [
            {
                "rule_id": "main-contact-filter",
                "object": "contact",
                "relation_path": [],
                "contact_mapping": {"type": "self", "field": "id"},
                "filter": {},
            }
        ],
        "exclude": [],
        "inherit_include_segment_ids": [],
        "inherit_exclude_segment_ids": [],
    }


def _related_config() -> dict:
    return {
        "root_object": "contact",
        "include": [
            {
                "rule_id": "applications",
                "object": "loan_application",
                "relation_path": ["loan_application.contact"],
                "contact_mapping": {"type": "field", "field": "contact_id"},
                "filter": {"field": "status", "op": "eq", "value": "approved"},
            }
        ],
        "exclude": [],
        "inherit_include_segment_ids": [],
        "inherit_exclude_segment_ids": [],
    }


def _segment(
    segment_id: SegmentIdVO,
    *,
    status: SegmentStatusVO = SegmentStatusVO.ACTIVE,
) -> SegmentDefinition:
    return SegmentDefinition(
        segment_id=segment_id,
        name="VIP",
        segment_kind=SegmentKindVO.DYNAMIC,
        status=status,
    )


class _MetadataStub:
    def __init__(self) -> None:
        self.objects = {
            "contact": _descriptor(
                "contact",
                fields=(
                    _field("id", "uuid"),
                    _field("status", "text"),
                ),
            ),
            "loan_application": _descriptor(
                "loan_application",
                table_name="loan_applications",
                fields=(
                    _field("id", "uuid"),
                    _field("status", "text"),
                    _field("contact_id", "uuid"),
                ),
            ),
        }
        self.relations = {
            ("loan_application", "contact"): SegmentVersionRuntimeRelationMetadata(
                name="contact",
                source_object="loan_application",
                target_object="contact",
                relation_type="many_to_one",
                fk_field="contact_id",
                referenced_object="contact",
                referenced_field="id",
                owning_object="loan_application",
            )
        }

    async def resolve_object(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        if object_name not in self.objects:
            raise LookupError(object_name)
        return self.objects[object_name]

    async def field_exists(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        field_name: str,
    ) -> bool:
        return (
            await self.field_type(
                tenant_id=tenant_id,
                object_name=object_name,
                field_name=field_name,
            )
            is not None
        )

    async def field_type(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        field_name: str,
    ) -> str | None:
        descriptor = self.objects.get(object_name)
        if descriptor is None:
            return None
        field = descriptor.field_by_name(field_name)
        return None if field is None else field.type_code

    async def resolve_relation(
        self,
        *,
        tenant_id: EntityIdVO,
        source_object: str,
        relation_name: str,
    ) -> SegmentVersionRuntimeRelationMetadata | None:
        return self.relations.get((source_object, relation_name))

    async def relation_exists(
        self,
        *,
        tenant_id: EntityIdVO,
        source_object: str,
        relation_name: str,
    ) -> bool:
        return (source_object, relation_name) in self.relations


class _FilterValidatorStub:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.calls: list[tuple[str, str]] = []

    async def validate_filter(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        filter_config,
        path: str,
    ) -> None:
        self.calls.append((object_name, path))
        if self.exc is not None:
            raise self.exc


class _SegmentRepositoryStub:
    def __init__(self, *segments: SegmentDefinition) -> None:
        self.segments = {segment.segment_id: segment for segment in segments}

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinition | None:
        return self.segments.get(segment_id)


class _ResolverStub:
    def __init__(self, descriptors: dict[str, RuntimeObjectDescriptor]) -> None:
        self.descriptors = descriptors

    async def resolve(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        return self.descriptors[object_name]


class _ObjectServiceStub:
    async def list_by_tenant_id(self, *, tenant_id: EntityIdVO):
        return [
            SimpleNamespace(
                object_name=SimpleNamespace(singular="contact", plural="contacts")
            ),
            SimpleNamespace(
                object_name=SimpleNamespace(
                    singular="loan_application",
                    plural="loan_applications",
                )
            ),
        ]


class SegmentVersionDslTests(unittest.IsolatedAsyncioTestCase):
    def test_parser_normalizes_missing_arrays_and_dumps_canonical_config(self) -> None:
        parsed = parse_segment_version_dsl_config({"root_object": "contact"})

        self.assertEqual(parsed.root_object, "contact")
        self.assertEqual(parsed.include, ())
        self.assertEqual(
            dump_segment_version_dsl_config(parsed),
            {
                "root_object": "contact",
                "include": [],
                "exclude": [],
                "inherit_include_segment_ids": [],
                "inherit_exclude_segment_ids": [],
            },
        )

    def test_parser_rejects_unknown_keys_invalid_root_and_duplicate_rule_ids(
        self,
    ) -> None:
        with self.assertRaises(SegmentVersionDslParseError):
            parse_segment_version_dsl_config(
                {"root_object": "contact", "unknown": True}
            )
        with self.assertRaises(SegmentVersionDslInvalidRootObjectError) as caught:
            parse_segment_version_dsl_config({"root_object": "company"})
        self.assertEqual(caught.exception.path, "root_object")

        config = _contact_config()
        config["exclude"] = [dict(config["include"][0])]
        with self.assertRaises(SegmentVersionDslInvalidRuleError):
            parse_segment_version_dsl_config(config)

    async def test_validator_accepts_contact_and_related_rules(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        filter_validator = _FilterValidatorStub()
        validator = SegmentVersionDslConfigValidator(
            metadata=_MetadataStub(),
            filter_validator=filter_validator,
            segment_definition_repository=_SegmentRepositoryStub(),
        )

        await validator.validate(tenant_id=tenant_id, config=_contact_config())
        related = await validator.validate(
            tenant_id=tenant_id, config=_related_config()
        )

        self.assertEqual(related.include[0].object, "loan_application")
        self.assertEqual(
            filter_validator.calls,
            [
                ("contact", "include[0].filter"),
                ("loan_application", "include[0].filter"),
            ],
        )

    async def test_validator_rejects_duplicate_rule_ids_in_typed_config(self) -> None:
        typed_config = parse_segment_version_dsl_config(_contact_config())
        typed_config = type(typed_config)(
            root_object=typed_config.root_object,
            include=typed_config.include,
            exclude=typed_config.include,
            inherit_include_segment_ids=typed_config.inherit_include_segment_ids,
            inherit_exclude_segment_ids=typed_config.inherit_exclude_segment_ids,
        )
        validator = SegmentVersionDslConfigValidator(
            metadata=_MetadataStub(),
            filter_validator=_FilterValidatorStub(),
            segment_definition_repository=_SegmentRepositoryStub(),
        )

        with self.assertRaises(SegmentVersionDslInvalidRuleError):
            await validator.validate(
                tenant_id=EntityIdVO.from_value(uuid4()),
                config=typed_config,
            )

    async def test_validator_rejects_limits_and_bad_relation_or_mapping(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        validator = SegmentVersionDslConfigValidator(
            metadata=_MetadataStub(),
            filter_validator=_FilterValidatorStub(),
            segment_definition_repository=_SegmentRepositoryStub(),
        )

        too_many = _contact_config()
        too_many["include"] = []
        for index in range(11):
            rule = dict(_contact_config()["include"][0])
            rule["rule_id"] = f"rule-{index}"
            too_many["include"].append(rule)
        with self.assertRaises(SegmentVersionDslRuleLimitError):
            await validator.validate(tenant_id=tenant_id, config=too_many)

        bad_relation = _related_config()
        bad_relation["include"][0]["relation_path"] = ["contact.contact"]
        with self.assertRaises(SegmentVersionDslInvalidRelationPathError):
            await validator.validate(tenant_id=tenant_id, config=bad_relation)

        bad_mapping = _related_config()
        bad_mapping["include"][0]["contact_mapping"]["field"] = "missing_id"
        with self.assertRaises(SegmentVersionDslInvalidContactMappingError):
            await validator.validate(tenant_id=tenant_id, config=bad_mapping)

    async def test_validator_checks_mapping_before_filter(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        config = _related_config()
        config["include"][0]["contact_mapping"]["field"] = "missing_id"
        validator = SegmentVersionDslConfigValidator(
            metadata=_MetadataStub(),
            filter_validator=_FilterValidatorStub(
                SegmentVersionDslValidationError(
                    "Bad filter.",
                    path="include[0].filter",
                )
            ),
            segment_definition_repository=_SegmentRepositoryStub(),
        )

        with self.assertRaises(SegmentVersionDslInvalidContactMappingError):
            await validator.validate(tenant_id=tenant_id, config=config)

    async def test_validator_rejects_inherited_self_missing_and_archived_segments(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        current_segment_id = SegmentIdVO.from_value(uuid4())
        archived_segment_id = SegmentIdVO.from_value(uuid4())
        validator = SegmentVersionDslConfigValidator(
            metadata=_MetadataStub(),
            filter_validator=_FilterValidatorStub(),
            segment_definition_repository=_SegmentRepositoryStub(
                _segment(
                    archived_segment_id,
                    status=SegmentStatusVO.ARCHIVED,
                )
            ),
        )

        self_config = _contact_config()
        self_config["inherit_include_segment_ids"] = [str(current_segment_id.uuid)]
        with self.assertRaises(SegmentVersionDslInvalidInheritedSegmentError):
            await validator.validate(
                tenant_id=tenant_id,
                config=self_config,
                current_segment_id=current_segment_id,
            )

        missing_config = _contact_config()
        missing_config["inherit_include_segment_ids"] = [str(uuid4())]
        with self.assertRaises(SegmentVersionDslInvalidInheritedSegmentError):
            await validator.validate(tenant_id=tenant_id, config=missing_config)

        archived_config = _contact_config()
        archived_config["inherit_include_segment_ids"] = [str(archived_segment_id.uuid)]
        with self.assertRaises(SegmentVersionDslInvalidInheritedSegmentError):
            await validator.validate(tenant_id=tenant_id, config=archived_config)

    async def test_filter_error_is_preserved_as_controlled_dsl_error(self) -> None:
        validator = SegmentVersionDslConfigValidator(
            metadata=_MetadataStub(),
            filter_validator=_FilterValidatorStub(
                SegmentVersionDslValidationError(
                    "Bad filter.", path="include[0].filter"
                )
            ),
            segment_definition_repository=_SegmentRepositoryStub(),
        )

        with self.assertRaises(SegmentVersionDslValidationError) as caught:
            await validator.validate(
                tenant_id=EntityIdVO.from_value(uuid4()),
                config=_contact_config(),
            )
        self.assertEqual(caught.exception.path, "include[0].filter")

    async def test_metadata_adapter_resolves_relation_with_singular_names(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        adapter = RuntimeObjectMetadataAdapter(
            runtime_object_resolver=_ResolverStub(
                {
                    "loan_application": _descriptor(
                        "loan_application",
                        table_name="loan_applications",
                        fields=(
                            _field("id", "uuid"),
                            _field("contact_id", "uuid"),
                        ),
                        relations=(_relation(),),
                    ),
                }
            ),
            object_service=_ObjectServiceStub(),
        )

        relation = await adapter.resolve_relation(
            tenant_id=tenant_id,
            source_object="loan_application",
            relation_name="contact",
        )

        self.assertEqual(relation.source_object, "loan_application")
        self.assertEqual(relation.target_object, "contact")
        self.assertEqual(relation.referenced_object, "contact")

    async def test_filter_adapter_accepts_runtime_data_group_filters(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        adapter = RuntimeFilterValidatorAdapter(
            runtime_object_resolver=_ResolverStub(
                {
                    "contact": _descriptor(
                        "contact",
                        fields=(
                            _field("id", "uuid"),
                            _field("status", "text"),
                        ),
                    )
                }
            )
        )

        await adapter.validate_filter(
            tenant_id=tenant_id,
            object_name="contact",
            filter_config={
                "and": [
                    {"field": "status", "op": "eq", "value": "customer"},
                ]
            },
            path="include[0].filter",
        )

    async def test_filter_adapter_wraps_runtime_data_errors_with_path(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        adapter = RuntimeFilterValidatorAdapter(
            runtime_object_resolver=_ResolverStub(
                {
                    "contact": _descriptor(
                        "contact",
                        fields=(_field("id", "uuid"),),
                    )
                }
            )
        )

        with self.assertRaises(SegmentVersionDslValidationError) as caught:
            await adapter.validate_filter(
                tenant_id=tenant_id,
                object_name="contact",
                filter_config={"field": "missing", "op": "eq", "value": "x"},
                path="include[0].filter",
            )
        self.assertEqual(caught.exception.path, "include[0].filter")


__all__ = ["SegmentVersionDslTests"]
