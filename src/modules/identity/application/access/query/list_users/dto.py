from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UserAccessDTO:
    id: UUID
    first_name: str
    last_name: str
    role: str
    status: str
    email: str | None
    cloud_linked: bool


@dataclass(frozen=True, slots=True)
class ListUsersResultDTO:
    users: list[UserAccessDTO]
