from typing import Annotated
from fastapi import Depends
from src.config import dnk_config
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.contact_points.infrastructure.persistence import (
    SqlAlchemyContactPointRepository,
    SqlAlchemyContactPointBindingRepository,
    SqlAlchemyContactPointLabelRepository,
)
from src.modules.contact_points.infrastructure.normalization.phone import (
    PhoneNormalizer,
)
from src.modules.contact_points.infrastructure.normalization.email import (
    EmailNormalizer,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.contact_point.normalization import (
    ContactPointNormalizerProtocol,
)


def get_tenant_naming():
    """Создаёт shared naming strategy для нового модуля."""
    return TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)


TenantNamingDep = Annotated[TenantSchemaNaming, Depends(get_tenant_naming)]


def get_contact_point_repository(uow: UoWDep, naming: TenantNamingDep):
    """Использует общую request-scoped session."""
    return SqlAlchemyContactPointRepository(uow.session, naming)


ContactPointRepositoryDep = Annotated[
    SqlAlchemyContactPointRepository, Depends(get_contact_point_repository)
]


def get_binding_repository(uow: UoWDep, naming: TenantNamingDep):
    """Собирает binding repository на той же session."""
    return SqlAlchemyContactPointBindingRepository(uow.session, naming)


ContactPointBindingRepositoryDep = Annotated[
    SqlAlchemyContactPointBindingRepository, Depends(get_binding_repository)
]


def get_label_repository(uow: UoWDep, naming: TenantNamingDep):
    """Собирает repository настроек без отдельного UoW."""
    return SqlAlchemyContactPointLabelRepository(uow.session, naming)


ContactPointLabelRepositoryDep = Annotated[
    SqlAlchemyContactPointLabelRepository, Depends(get_label_repository)
]


def get_normalizers():
    """Сопоставляет поддерживаемые типы с их валидаторами."""
    return {
        ContactPointType.PHONE: PhoneNormalizer(),
        ContactPointType.EMAIL: EmailNormalizer(),
    }


ContactPointNormalizersDep = Annotated[
    dict[ContactPointType, ContactPointNormalizerProtocol], Depends(get_normalizers)
]

__all__ = [
    "ContactPointRepositoryDep",
    "ContactPointBindingRepositoryDep",
    "ContactPointLabelRepositoryDep",
    "ContactPointNormalizersDep",
    "get_contact_point_repository",
    "get_binding_repository",
    "get_label_repository",
    "get_normalizers",
    "get_tenant_naming",
]
