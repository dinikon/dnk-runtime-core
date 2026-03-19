from src.modules.crm.infrastructure.repositories import (
    FakeContactCommandRepository,
    FakeContactQueryRepository,
    get_fake_contacts_storage,
)

__all__ = [
    "FakeContactCommandRepository",
    "FakeContactQueryRepository",
    "get_fake_contacts_storage",
]
