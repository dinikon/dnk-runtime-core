from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.content_block.command.create_content_block.handler import (
    CreateContentBlockHandler,
)
from src.modules.catalog.application.content_block.command.delete_content_block.handler import (
    DeleteContentBlockHandler,
)
from src.modules.catalog.application.content_block.command.put_content_block.handler import (
    PutContentBlockHandler,
)
from src.modules.catalog.application.content_block.query.get_content_block.handler import (
    GetContentBlockHandler,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.handler import (
    ListContentBlocksHandler,
)
from src.modules.catalog.infrastructure.content_block.persistence.query_repository import (
    SqlAlchemyContentBlockQueryRepository,
)
from src.modules.catalog.infrastructure.content_block.persistence.repository import (
    SqlAlchemyContentBlockRepository,
)
from src.modules.catalog.infrastructure.content_block.persistence.usage_reader import (
    SqlAlchemyContentBlockUsageReader,
)
from src.modules.catalog.infrastructure.reference_locale_reader import (
    ReferenceLocaleReaderAdapter,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_create_content_block_handler(
    uow: UoWDep, uuids: UuidDep
) -> CreateContentBlockHandler:
    return CreateContentBlockHandler(
        SqlAlchemyContentBlockRepository(uow.session),
        ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session)),
        uuids,
    )


CreateContentBlockHandlerDep = Annotated[
    CreateContentBlockHandler, Depends(get_create_content_block_handler)
]


def get_put_content_block_handler(uow: UoWDep) -> PutContentBlockHandler:
    return PutContentBlockHandler(
        SqlAlchemyContentBlockRepository(uow.session),
        SqlAlchemyContentBlockUsageReader(uow.session),
        ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session)),
    )


PutContentBlockHandlerDep = Annotated[
    PutContentBlockHandler, Depends(get_put_content_block_handler)
]


def get_delete_content_block_handler(uow: UoWDep) -> DeleteContentBlockHandler:
    return DeleteContentBlockHandler(
        SqlAlchemyContentBlockRepository(uow.session),
        SqlAlchemyContentBlockUsageReader(uow.session),
    )


DeleteContentBlockHandlerDep = Annotated[
    DeleteContentBlockHandler, Depends(get_delete_content_block_handler)
]


def get_get_content_block_handler(uow: UoWDep) -> GetContentBlockHandler:
    return GetContentBlockHandler(SqlAlchemyContentBlockQueryRepository(uow.session))


GetContentBlockHandlerDep = Annotated[
    GetContentBlockHandler, Depends(get_get_content_block_handler)
]


def get_list_content_blocks_handler(uow: UoWDep) -> ListContentBlocksHandler:
    return ListContentBlocksHandler(SqlAlchemyContentBlockQueryRepository(uow.session))


ListContentBlocksHandlerDep = Annotated[
    ListContentBlocksHandler, Depends(get_list_content_blocks_handler)
]
