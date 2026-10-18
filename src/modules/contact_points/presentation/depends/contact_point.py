from typing import Annotated

from fastapi import Depends

from src.modules.contact_points.domain.normalization import (
    ContactPointNormalizerProtocol,
)
from src.modules.contact_points.domain.resolver import ContactPointResolver
from src.modules.contact_points.domain.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.infrastructure.normalization.email import (
    EmailNormalizer,
)
from src.modules.contact_points.infrastructure.normalization.phone import (
    PhoneNormalizer,
)
from src.modules.contact_points.infrastructure.persistence.contact_point_repository import (
    SqlAlchemyContactPointRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


def get_contact_point_repository(uow: UoWDep) -> SqlAlchemyContactPointRepository:
    """Собирает справочник точек на общей request-scoped сессии."""
    return SqlAlchemyContactPointRepository(uow.session)


ContactPointRepositoryDep = Annotated[
    SqlAlchemyContactPointRepository, Depends(get_contact_point_repository)
]


def get_normalizers() -> dict[ContactPointType, ContactPointNormalizerProtocol]:
    """Сопоставляет поддерживаемые типы с валидаторами."""
    return {
        ContactPointType.PHONE: PhoneNormalizer(),
        ContactPointType.EMAIL: EmailNormalizer(),
    }


ContactPointNormalizersDep = Annotated[
    dict[ContactPointType, ContactPointNormalizerProtocol], Depends(get_normalizers)
]


def get_contact_point_resolver(
    repository: ContactPointRepositoryDep,
    normalizers: ContactPointNormalizersDep,
    clock: ClockDep,
) -> ContactPointResolver:
    """Собирает resolver без доступа к UoW из Domain."""
    return ContactPointResolver(repository, normalizers, clock)


ContactPointResolverDep = Annotated[
    ContactPointResolver, Depends(get_contact_point_resolver)
]
