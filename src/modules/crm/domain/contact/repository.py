from typing import Protocol

from modules.crm.domain import ContactEntity


class ContactRepositoryPort(Protocol):
    def list(
        self,
    ) -> list[ContactEntity]: ...

    def get_by_id(
        self,
    ) -> ContactEntity | None: ...
