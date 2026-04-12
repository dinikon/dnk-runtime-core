from __future__ import annotations

from src.modules.schema_registry.presentation.depends.infrastructure import (
    DataSourceServiceDep as _DataSourceServiceDep,
    FieldTypeCatalogDep as _FieldTypeCatalogDep,
    ObjectServiceDep as _ObjectServiceDep,
)

DataSourceServiceDep = _DataSourceServiceDep
FieldTypeCatalogDep = _FieldTypeCatalogDep
ObjectServiceDep = _ObjectServiceDep

__all__ = [
    "DataSourceServiceDep",
    "FieldTypeCatalogDep",
    "ObjectServiceDep",
]
