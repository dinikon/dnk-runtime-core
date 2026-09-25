from src.modules.contact_points.infrastructure.persistence.repository.contact_point_repository import (
    SqlAlchemyContactPointRepository,
)
from src.modules.contact_points.infrastructure.persistence.repository.binding_repository import (
    SqlAlchemyContactPointBindingRepository,
)
from src.modules.contact_points.infrastructure.persistence.repository.label_repository import (
    SqlAlchemyContactPointLabelRepository,
)

__all__ = [
    "SqlAlchemyContactPointRepository",
    "SqlAlchemyContactPointBindingRepository",
    "SqlAlchemyContactPointLabelRepository",
]
