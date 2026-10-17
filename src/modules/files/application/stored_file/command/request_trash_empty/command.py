from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestTrashEmptyCommand:
    """Запрашивает очистку текущей корзины доверенного tenant от имени администратора."""

    tenant_id: UUID
    actor_id: UUID
