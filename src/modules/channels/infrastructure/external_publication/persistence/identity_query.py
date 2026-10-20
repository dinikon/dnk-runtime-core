from uuid import UUID
from sqlalchemy import select, func, literal, case, cast, Text
from sqlalchemy.sql.selectable import CTE
from src.modules.channels.application.external_publication.identity_contract import (
    PublicationIdentityPolicyDTO,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)


def publication_identity_projection(
    connection_id: UUID, policy: PublicationIdentityPolicyDTO | None
) -> CTE:
    """Считает коллизии по всему Connection до фильтров строки и пагинации."""
    table = ExternalPublicationModel.__table__
    if policy is None:
        return (
            select(
                table.c.id,
                literal("not_required").label("identity_state"),
                cast(literal(None), Text()).label("identity_key"),
                literal(0).label("identity_conflict_count"),
            )
            .where(table.c.connection_id == connection_id)
            .cte("publication_identity")
        )
    key = table.c.meta[policy.key_path].astext
    counted = (
        select(
            table.c.id,
            key.label("identity_key"),
            func.count().over(partition_by=key).label("key_count"),
        )
        .where(table.c.connection_id == connection_id)
        .cte("identity_counts")
    )
    missing = (
        func.coalesce(func.btrim(counted.c.identity_key, " \t\n\r\v\f\u00a0"), "") == ""
    )
    return select(
        counted.c.id,
        case(
            (missing, "missing"), (counted.c.key_count > 1, "duplicate"), else_="valid"
        ).label("identity_state"),
        counted.c.identity_key,
        case((missing, 0), else_=counted.c.key_count - 1).label(
            "identity_conflict_count"
        ),
    ).cte("publication_identity")
