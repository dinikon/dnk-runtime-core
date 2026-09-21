from typing import Annotated
from fastapi import Depends
from src.config import dnk_config
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.events.sqlalchemy_outbox_repository import (
    SqlAlchemyOutboxRepository,
)
from src.modules.identity.infrastructure.repository.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.currency.display_currency_validator import (
    CurrencyDisplayCurrencyValidator,
)
from src.modules.identity.application.user.use_case.set_display_currency import (
    SetDisplayCurrencyUseCase,
)
from src.modules.currency.application.settings.use_case.validate_display_currency import (
    ValidateDisplayCurrencyUseCase,
)
from src.modules.currency.presentation.depends.infrastructure import (
    CurrencyRepositoriesDep,
)


def get_display_currency_preferences(uow: UoWDep) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(
        uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    )


DisplayCurrencyPreferencesDep = Annotated[
    SqlAlchemyUserRepository, Depends(get_display_currency_preferences)
]


def get_set_display_currency_use_case(
    users: DisplayCurrencyPreferencesDep,
    repositories: CurrencyRepositoriesDep,
    uow: UoWDep,
    clock: ClockDep,
) -> SetDisplayCurrencyUseCase:
    validator = CurrencyDisplayCurrencyValidator(
        ValidateDisplayCurrencyUseCase(
            repositories.directory, repositories.policies, repositories.enabled
        )
    )
    return SetDisplayCurrencyUseCase(
        users, validator, SqlAlchemyOutboxRepository(uow.session), clock
    )


SetDisplayCurrencyUseCaseDep = Annotated[
    SetDisplayCurrencyUseCase, Depends(get_set_display_currency_use_case)
]

__all__ = [
    "DisplayCurrencyPreferencesDep",
    "SetDisplayCurrencyUseCaseDep",
    "get_set_display_currency_use_case",
]
