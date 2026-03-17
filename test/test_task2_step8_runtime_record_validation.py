from __future__ import annotations

import json
import unittest
from uuid import UUID, uuid4

from src.modules.runtime_record.application import (
    ReadRuntimeValuesQuery,
    RuntimeRecordApplicationService,
    WriteRuntimeValuesCommand,
)
from src.modules.runtime_record.domain.errors import RuntimeRecordValidationError
from src.modules.runtime_schema.domain.entities import DataSource, FieldMetadata, ObjectMetadata
from src.modules.runtime_schema.domain.value_objects import FieldType, ObjectOwnershipKind


class _FakeUoW:
    def __init__(self) -> None:
        self.session = None
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> "_FakeUoW":
        self.session = object()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            await self.rollback()
        self.session = None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _FakeObjectMetadataRepository:
    def __init__(self, object_metadata: ObjectMetadata):
        self._object_metadata = object_metadata

    async def get_by_name(
        self,
        *,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None:
        if (
            self._object_metadata.tenant_id == tenant_id
            and self._object_metadata.name_singular == name_singular
        ):
            return self._object_metadata
        return None


class _FakeFieldMetadataRepository:
    def __init__(self, fields: tuple[FieldMetadata, ...]):
        self._fields = fields

    async def list_by_object_metadata_id(
        self,
        object_metadata_id: UUID,
    ) -> tuple[FieldMetadata, ...]:
        return tuple(
            field for field in self._fields if field.object_metadata_id == object_metadata_id
        )


class _FakeDataSourceRepository:
    def __init__(self, data_source: DataSource):
        self._data_source = data_source

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None:
        if self._data_source.id == data_source_id:
            return self._data_source
        return None


class _FakeRuntimeValueRepository:
    def __init__(self) -> None:
        self.write_calls: list[dict[str, object]] = []
        self.read_payload: dict[str, object | None] = {}

    async def write_values(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        record_id: UUID,
        values: dict[str, object | None],
    ) -> None:
        self.write_calls.append(
            {
                "schema_name": schema_name,
                "table_name": table_name,
                "record_id": record_id,
                "values": values,
            }
        )
        self.read_payload = dict(values)

    async def read_values(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        record_id: UUID,
        field_names: tuple[str, ...],
    ) -> dict[str, object | None]:
        result: dict[str, object | None] = {}
        for field_name in field_names:
            value = self.read_payload.get(field_name)
            if isinstance(value, list):
                result[field_name] = json.dumps(value)
            else:
                result[field_name] = value
        return result


class TestRuntimeRecordValidationStep8(unittest.IsolatedAsyncioTestCase):
    async def test_write_values_rejects_unknown_fields(self) -> None:
        service = self._build_service(
            fields=(
                self._field(name="telegram", field_type=FieldType.STRING, is_nullable=True),
            )
        )

        with self.assertRaises(RuntimeRecordValidationError):
            await service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=self._tenant_id,
                    object_name_singular="contact",
                    record_id=uuid4(),
                    values={"unknown": "value"},
                )
            )

    async def test_write_values_rejects_missing_required_field(self) -> None:
        service = self._build_service(
            fields=(
                self._field(name="telegram", field_type=FieldType.STRING, is_nullable=False),
            )
        )

        with self.assertRaises(RuntimeRecordValidationError):
            await service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=self._tenant_id,
                    object_name_singular="contact",
                    record_id=uuid4(),
                    values={},
                )
            )

    async def test_write_values_rejects_invalid_number_type(self) -> None:
        service = self._build_service(
            fields=(self._field(name="score", field_type=FieldType.NUMBER, is_nullable=False),)
        )

        with self.assertRaises(RuntimeRecordValidationError):
            await service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=self._tenant_id,
                    object_name_singular="contact",
                    record_id=uuid4(),
                    values={"score": "high"},
                )
            )

    async def test_write_values_rejects_invalid_select_option(self) -> None:
        service = self._build_service(
            fields=(
                self._field(
                    name="category",
                    field_type=FieldType.SELECT,
                    is_nullable=False,
                    options=("vendor", "partner"),
                ),
            )
        )

        with self.assertRaises(RuntimeRecordValidationError):
            await service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=self._tenant_id,
                    object_name_singular="contact",
                    record_id=uuid4(),
                    values={"category": "client"},
                )
            )

    async def test_write_and_read_values_accepts_valid_payload(self) -> None:
        runtime_repository = _FakeRuntimeValueRepository()
        service = self._build_service(
            fields=(
                self._field(name="telegram", field_type=FieldType.STRING, is_nullable=False),
                self._field(
                    name="tags",
                    field_type=FieldType.MULTISELECT,
                    is_nullable=True,
                    options=("vip", "partner"),
                ),
            ),
            runtime_repository=runtime_repository,
        )
        record_id = uuid4()

        write_result = await service.write_values(
            WriteRuntimeValuesCommand(
                tenant_id=self._tenant_id,
                object_name_singular="contact",
                record_id=record_id,
                values={"telegram": "@john", "tags": ["vip"]},
            )
        )

        self.assertEqual(write_result.values["telegram"], "@john")
        self.assertEqual(write_result.values["tags"], ["vip"])
        self.assertEqual(len(runtime_repository.write_calls), 1)

        read_result = await service.read_values(
            ReadRuntimeValuesQuery(
                tenant_id=self._tenant_id,
                object_name_singular="contact",
                record_id=record_id,
            )
        )

        self.assertEqual(read_result.values["telegram"], "@john")
        self.assertEqual(read_result.values["tags"], ["vip"])

    def _build_service(
        self,
        *,
        fields: tuple[FieldMetadata, ...],
        runtime_repository: _FakeRuntimeValueRepository | None = None,
    ) -> RuntimeRecordApplicationService:
        self._tenant_id = uuid4()
        data_source = DataSource.create(tenant_id=self._tenant_id)
        object_metadata = ObjectMetadata.create(
            tenant_id=self._tenant_id,
            data_source_id=data_source.id,
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )

        rewritten_fields = tuple(
            FieldMetadata(
                id=field.id,
                created_at=field.created_at,
                updated_at=field.updated_at,
                object_metadata_id=object_metadata.id,
                type=field.type,
                name=field.name,
                label=field.label,
                default_value=field.default_value,
                description=field.description,
                icon=field.icon,
                options=field.options,
                settings=field.settings,
                is_active=field.is_active,
                is_nullable=field.is_nullable,
                is_unique=field.is_unique,
                tenant_id=field.tenant_id,
            )
            for field in fields
        )

        uow = _FakeUoW()
        return RuntimeRecordApplicationService(
            uow=uow,
            object_metadata_repository=_FakeObjectMetadataRepository(object_metadata),
            field_metadata_repository=_FakeFieldMetadataRepository(rewritten_fields),
            data_source_repository=_FakeDataSourceRepository(data_source),
            runtime_value_repository=runtime_repository or _FakeRuntimeValueRepository(),
        )

    def _field(
        self,
        *,
        name: str,
        field_type: FieldType,
        is_nullable: bool,
        options: tuple[str, ...] = (),
    ) -> FieldMetadata:
        return FieldMetadata.create(
            object_metadata_id=uuid4(),
            tenant_id=uuid4(),
            field_type=field_type,
            name=name,
            label=name,
            options=options,
            is_nullable=is_nullable,
        )


if __name__ == "__main__":
    unittest.main()
