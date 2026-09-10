from src.modules.shared.presentation.identity_context.authenticate_by_session_command import (
    AuthenticateBySessionCommand,
)
from src.modules.shared.presentation.identity_context.authenticate_by_session_use_case_adapter import (
    AuthenticateBySessionUseCaseAdapter,
)
from src.modules.shared.presentation.identity_context.authentication_process_protocol import (
    AuthenticationProcessProtocol,
)
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
    AuthenticationProcessDep,
    OptionalRequestContextDep,
    get_authentication_process,
    get_optional_request_context,
    require_authenticated_request_context,
)

__all__ = [
    "AuthenticatedRequestContextDep",
    "AuthenticateBySessionCommand",
    "AuthenticateBySessionUseCaseAdapter",
    "AuthenticationProcessDep",
    "AuthenticationProcessProtocol",
    "OptionalRequestContextDep",
    "get_authentication_process",
    "get_optional_request_context",
    "require_authenticated_request_context",
]
