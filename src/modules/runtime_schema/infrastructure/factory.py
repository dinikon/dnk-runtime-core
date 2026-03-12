from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.infrastructure.ddl_diff_engine import DdlDiffEngine
from src.modules.runtime_schema.infrastructure.ddl_executor import SqlAlchemyDdlExecutor
from src.modules.runtime_schema.infrastructure.ddl_orchestrator_service import (
    DdlOrchestratorService,
)
from src.modules.runtime_schema.infrastructure.ddl_plan_builder import DdlPlanBuilder
from src.modules.runtime_schema.infrastructure.field_layout_compiler import (
    FieldLayoutCompiler,
)
from src.modules.runtime_schema.infrastructure.metadata_compiler import MetadataCompiler
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
    SqlAlchemySchemaMigrationJournalRepository,
    SqlAlchemySchemaVersionRepository,
)
from src.modules.runtime_schema.infrastructure.schema_introspector import (
    SqlAlchemySchemaIntrospector,
)
from src.modules.runtime_schema.infrastructure.schema_lock import SqlAlchemySchemaLockService
from src.modules.runtime_schema.infrastructure.system_manifest_reader import (
    YamlSystemModelRegistryReader,
)


def default_system_manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "system_models"
        / "system_models.yaml"
    )


def build_ddl_orchestrator(
    *,
    session: AsyncSession,
    manifest_path: Path | None = None,
) -> DdlOrchestratorService:
    bind = session.get_bind()
    dialect_name = bind.dialect.name.lower()
    return DdlOrchestratorService(
        registry_reader=YamlSystemModelRegistryReader(
            manifest_path=manifest_path or default_system_manifest_path()
        ),
        metadata_compiler=MetadataCompiler(),
        field_layout_compiler=FieldLayoutCompiler(),
        schema_introspector=SqlAlchemySchemaIntrospector(session),
        ddl_diff_engine=DdlDiffEngine(),
        ddl_plan_builder=DdlPlanBuilder(dialect_name=dialect_name),
        ddl_executor=SqlAlchemyDdlExecutor(session),
        schema_version_repository=SqlAlchemySchemaVersionRepository(session),
        schema_migration_journal_repository=SqlAlchemySchemaMigrationJournalRepository(
            session
        ),
        schema_lock_service=SqlAlchemySchemaLockService(session),
        object_metadata_repository=SqlAlchemyObjectMetadataRepository(session),
        field_metadata_repository=SqlAlchemyFieldMetadataRepository(session),
    )


__all__ = [
    "build_ddl_orchestrator",
    "default_system_manifest_path",
]
