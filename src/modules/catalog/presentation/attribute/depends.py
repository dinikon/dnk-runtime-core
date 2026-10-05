from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.attribute.command.create_attribute.handler import (
    CreateAttributeHandler,
)
from src.modules.catalog.application.attribute.port.locale_reader import (
    AttributeLocaleReaderPort,
)
from src.modules.catalog.application.attribute.query.get_attribute.handler import (
    GetAttributeHandler,
)
from src.modules.catalog.application.attribute.query.list_attributes.handler import (
    ListAttributesHandler,
)
from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.catalog.infrastructure.attribute.persistence.query_repository import (
    SqlAlchemyAttributeQueryRepository,
)
from src.modules.catalog.infrastructure.attribute.persistence.repository import (
    SqlAlchemyAttributeRepository,
)
from src.modules.catalog.infrastructure.reference_locale_reader import (
    ReferenceLocaleReaderAdapter,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_attribute_repository(uow: UoWDep) -> AttributeRepositoryProtocol:
    return SqlAlchemyAttributeRepository(uow.session)


AttributeRepositoryDep = Annotated[
    AttributeRepositoryProtocol, Depends(get_attribute_repository)
]


def get_attribute_query_repository(uow: UoWDep) -> SqlAlchemyAttributeQueryRepository:
    return SqlAlchemyAttributeQueryRepository(uow.session)


AttributeQueryRepositoryDep = Annotated[
    SqlAlchemyAttributeQueryRepository, Depends(get_attribute_query_repository)
]


def get_attribute_locale_reader(uow: UoWDep) -> AttributeLocaleReaderPort:
    return ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session))


AttributeLocaleReaderDep = Annotated[
    AttributeLocaleReaderPort, Depends(get_attribute_locale_reader)
]


def get_create_attribute_handler(
    repository: AttributeRepositoryDep,
    locales: AttributeLocaleReaderDep,
    clock: ClockDep,
    uuids: UuidDep,
) -> CreateAttributeHandler:
    return CreateAttributeHandler(repository, locales, clock, uuids)


CreateAttributeHandlerDep = Annotated[
    CreateAttributeHandler, Depends(get_create_attribute_handler)
]


def get_list_attributes_handler(
    repository: AttributeQueryRepositoryDep,
) -> ListAttributesHandler:
    return ListAttributesHandler(repository)


ListAttributesHandlerDep = Annotated[
    ListAttributesHandler, Depends(get_list_attributes_handler)
]


def get_get_attribute_handler(
    repository: AttributeQueryRepositoryDep,
) -> GetAttributeHandler:
    return GetAttributeHandler(repository)


GetAttributeHandlerDep = Annotated[
    GetAttributeHandler, Depends(get_get_attribute_handler)
]
