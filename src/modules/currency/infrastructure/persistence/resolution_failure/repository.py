from sqlalchemy.dialects.postgresql import insert
from src.modules.currency.domain.resolution_failure.entity import ResolutionFailure
from src.modules.currency.infrastructure.persistence.resolution_failure.model import (
    ResolutionFailureModel,
)
from src.modules.currency.infrastructure.persistence.scoped_repository import (
    ScopedRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlResolutionFailureRepository(ScopedRepository):
    """Atomically claim an operation's diagnostic key."""

    async def add_once(
        self, *, tenant_id: EntityIdVO, failure: ResolutionFailure
    ) -> bool:
        table = ResolutionFailureModel.__table__
        result = await self.session.execute(
            self.scoped(
                insert(table)
                .values(
                    id=failure.id.uuid,
                    operation_id=failure.operation_id.uuid,
                    source_currency=str(failure.source),
                    target_currency=str(failure.target) if failure.target else None,
                    business_date=failure.business_date,
                    provider_code=str(failure.provider) if failure.provider else None,
                    policy_version=failure.policy_version,
                    error_code=failure.error_code,
                    occurred_at=failure.occurred_at,
                    deduplication_key=failure.deduplication_key,
                )
                .on_conflict_do_nothing(index_elements=[table.c.deduplication_key])
                .returning(table.c.id),
                tenant_id,
            )
        )
        return result.scalar_one_or_none() is not None


__all__ = ["SqlResolutionFailureRepository"]
