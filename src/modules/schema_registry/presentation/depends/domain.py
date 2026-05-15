from __future__ import annotations

from src.modules.schema_registry.presentation.depends.infrastructure import (
    DataSourceServiceDep as _DataSourceServiceDep,
    FieldTypeCatalogDep as _FieldTypeCatalogDep,
    ObjectServiceDep as _ObjectServiceDep,
    RelationServiceDep as _RelationServiceDep,
)

DataSourceServiceDep = _DataSourceServiceDep
FieldTypeCatalogDep = _FieldTypeCatalogDep
ObjectServiceDep = _ObjectServiceDep
RelationServiceDep = _RelationServiceDep

__all__ = [
    "DataSourceServiceDep",
    "FieldTypeCatalogDep",
    "ObjectServiceDep",
    "RelationServiceDep",
]
