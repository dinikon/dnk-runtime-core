from src.modules.schema_registry.infrastructure.repository.object_repository import (
    SqlAlchemyObjectRepository as _ObjectRepository,
)

ObjectRepository = _ObjectRepository

__all__ = ["ObjectRepository"]
