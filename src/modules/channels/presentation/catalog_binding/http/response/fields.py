from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Literal


class PositionFields(BaseModel):
    """Только публичные поля сравнения без native JSON и секретов."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: str
    title: str | None
    sku: str | None
    image_url: str | None
    status: str | None
    price: str | None
    currency: str | None
    quantity: str | None
    availability: str | None
    stock_source_id: UUID
    external_id: str | None
    stale: bool


class PairFields(BaseModel):
    """Явное соответствие продаваемых позиций."""

    model_config = ConfigDict(from_attributes=True)
    catalog_position_id: UUID
    publication_id: UUID


class FamilyStructureFields(BaseModel):
    """Публичная идентичность и роль семьи."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: str
    positions: list[UUID]


class CatalogFamilyFields(BaseModel):
    """Эффективные превью семьи Catalog."""

    model_config = ConfigDict(from_attributes=True)
    structure: FamilyStructureFields
    root: PositionFields
    positions: list[PositionFields]


class AssessmentFields(BaseModel):
    """Полнота по известным данным отдельно от доступности экспорта."""

    model_config = ConfigDict(from_attributes=True)
    state: Literal["linked", "partial", "conflict"]
    issues: list[str]
    catalog_count: int
    publication_count: int
    matched_count: int


class PreviewFields(BaseModel):
    """Контекст предложения без побочных эффектов."""

    model_config = ConfigDict(from_attributes=True)
    catalog: CatalogFamilyFields | None
    publications: list[PositionFields]
    assessment: AssessmentFields
    catalog_token: str
    publication_token: str
    suggestions: list[PairFields]


class GroupRecordFields(BaseModel):
    """Собственные поля группы и её ревизия."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    connection_id: UUID
    channel_id: UUID
    channel_name: str
    platform: str
    catalog_root_id: UUID
    mode: Literal["SIMPLE_TO_SIMPLE", "VARIABLE_TO_VARIABLE", "VARIABLE_TO_SIMPLE"]
    publication_root_id: UUID | None
    revision: int
    items: list[PairFields]
    created_at: datetime
    updated_at: datetime


class GroupFields(BaseModel):
    """Группа и вычисляемое состояние для обоих интерфейсов."""

    model_config = ConfigDict(from_attributes=True)
    group: GroupRecordFields
    preview: PreviewFields
