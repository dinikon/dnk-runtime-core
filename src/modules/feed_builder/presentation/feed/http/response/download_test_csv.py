from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TestCsvIssueResponse(BaseModel):
    """Привязывает блокирующую ошибку файла к публикации и полю."""

    model_config = ConfigDict(from_attributes=True)
    publication_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    sku: str | None
    field_id: UUID | None
    field_name: str | None
    code: str
    message: str
    path: tuple[str | int, ...]
    rule_id: UUID | None


class DownloadTestCsvErrorResponse(BaseModel):
    """Возвращает причину, по которой файл не был собран."""

    code: str
    message: str
    issues: tuple[TestCsvIssueResponse, ...]
