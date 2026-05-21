from src.modules.contact_point.presentation.depends.application import (
    AttachContactPointUseCaseDep,
    DetachContactPointUseCaseDep,
)
from src.modules.contact_point.presentation.depends.infrastructure import (
    ContactPointHashServiceDep,
    ContactPointNormalizerDep,
    ContactPointObjectFeatureGateDep,
    ContactPointRuntimeRepositoryDep,
    OwnerResolverDep,
)

__all__ = [
    "AttachContactPointUseCaseDep",
    "ContactPointHashServiceDep",
    "ContactPointNormalizerDep",
    "ContactPointObjectFeatureGateDep",
    "ContactPointRuntimeRepositoryDep",
    "DetachContactPointUseCaseDep",
    "OwnerResolverDep",
]
