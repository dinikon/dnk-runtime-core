from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.content_schema.service import ContentSchemaService
from src.modules.catalog.presentation.product.depends import (
    ContentSchemaRepositoryDep,
    LocaleReaderDep,
)
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_content_schema_service(
    repository: ContentSchemaRepositoryDep, locales: LocaleReaderDep, uuids: UuidDep
) -> ContentSchemaService:
    return ContentSchemaService(repository, locales, uuids)


ContentSchemaServiceDep = Annotated[
    ContentSchemaService, Depends(get_content_schema_service)
]
