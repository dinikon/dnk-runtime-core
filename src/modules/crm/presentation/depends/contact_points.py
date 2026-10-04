from typing import Annotated

from fastapi import Depends

from src.modules.contact_points.presentation.depends.application import (
    GetTargetsContactPointsUseCaseDep,
    RemoveTargetContactPointsUseCaseDep,
    SyncTargetContactPointsUseCaseDep,
)
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.infrastructure.contact_point.adapter import ContactPointsAdapter
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_contact_contact_points(
    reader: GetTargetsContactPointsUseCaseDep,
    writer: SyncTargetContactPointsUseCaseDep,
    remover: RemoveTargetContactPointsUseCaseDep,
    uuid_generator: UuidDep,
) -> ContactPointsPort:
    """Подключает расширение Contact на общей сессии HTTP UoW."""
    return ContactPointsAdapter("crm.contact", reader, writer, remover, uuid_generator)


ContactContactPointsDep = Annotated[
    ContactPointsPort, Depends(get_contact_contact_points)
]


def get_company_contact_points(
    reader: GetTargetsContactPointsUseCaseDep,
    writer: SyncTargetContactPointsUseCaseDep,
    remover: RemoveTargetContactPointsUseCaseDep,
    uuid_generator: UuidDep,
) -> ContactPointsPort:
    """Подключает расширение Company на общей сессии HTTP UoW."""
    return ContactPointsAdapter("crm.company", reader, writer, remover, uuid_generator)


CompanyContactPointsDep = Annotated[
    ContactPointsPort, Depends(get_company_contact_points)
]
