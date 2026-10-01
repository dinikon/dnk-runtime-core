from fastapi import Depends
from src.modules.identity.application.invitation.service.validator import (
    InvitationValidator,
)
from src.modules.identity.presentation.access.providers import AccessRepositoryDep
from typing import Annotated


def get_invitation_validator(access: AccessRepositoryDep) -> InvitationValidator:
    return InvitationValidator(access=access)


InvitationValidatorDep = Annotated[
    InvitationValidator, Depends(get_invitation_validator)
]
